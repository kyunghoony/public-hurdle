"""CLI — python -m hurdle.cli <command>"""
import argparse
import csv
import sys
from .config import load_config
from .models import Ticker
from .engine import quality, regime, hurdle as hurdle_mod
from . import deal as deal_mod
from . import report

COLS = ["ticker", "market", "ccy", "sector", "subsector", "mcap", "ttmRev", "ttmFCF",
        "margin3y", "growth", "roic", "ndEbitda", "cagr", "ret1m", "ret3m", "ret6m", "off52w"]


def read_universe(path: str) -> list[Ticker]:
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            g = lambda k: float(row[k]) if row.get(k, "").strip() else 0.0
            gn = lambda k: float(row[k]) if row.get(k, "").strip() else None
            out.append(Ticker(symbol=row["ticker"], market=row["market"], ccy=row["ccy"],
                              sector=row["sector"], subsector=row.get("subsector") or None,
                              mcap=g("mcap"), ttm_rev=g("ttmRev"), ttm_fcf=g("ttmFCF"),
                              fcf_margin_3y=g("margin3y"), growth=g("growth"), roic_3y=g("roic"),
                              netdebt_ebitda=g("ndEbitda"), rev_cagr_3y=g("cagr"),
                              ret_1m=gn("ret1m"), ret_3m=gn("ret3m"), ret_6m=gn("ret6m"),
                              off_52w_high=gn("off52w"), source="csv"))
    return out


def cmd_hurdle(args):
    cfg = load_config(args.config)
    rows = read_universe(args.universe)
    evaluated = [(t, quality.evaluate(t, cfg)) for t in rows]
    reg = regime.classify(rows, cfg)
    H = hurdle_mod.compute(evaluated, cfg)
    print(f"레짐: {reg.tag} (3M {reg.ret_3m and round(reg.ret_3m,1)}%, 고점比 {reg.off_52w and round(reg.off_52w,1)}%, n={reg.n})")
    print(f"품질 통과: {H.pool_count} / {len(rows)}")
    if H.hurdle is not None:
        print(f"바스켓(top-3 {', '.join(H.top3)}): {H.basket*100:.1f}% + 프리미엄 {H.premium*100:.1f}%p = 허들 {H.hurdle*100:.1f}%")
    else:
        print("허들 계산 불가 — 품질 통과 3종목 미만. 재무 데이터를 입력할 것.")
    for t, v in sorted(evaluated, key=lambda x: -(x[1].r_star or -1)):
        r = f"{v.r_star*100:.1f}%" if v.r_star is not None else "입력부족"
        tags = (" [cycle-peak]" if v.cycle_peak else "") + ("" if v.quality_pass else f" [탈락: {','.join(v.quality_fails)}]")
        print(f"  {t.symbol:<14s} r*={r:<8s} 3M={t.ret_3m}{tags}")


def cmd_deal(args):
    cfg = load_config(args.config)
    rows = read_universe(args.universe)
    evaluated = [(t, quality.evaluate(t, cfg)) for t in rows]
    d = deal_mod.load_deal(args.deal)
    sub = d.get("subsector")
    reg_rows = [t for t in rows if t.subsector == sub] if sub else rows
    reg = regime.classify(reg_rows, cfg)
    if reg.tag == "표본부족":
        reg = regime.classify(rows, cfg)
    H = hurdle_mod.compute(evaluated, cfg)
    result = deal_mod.evaluate_deal(d, H, reg, cfg)
    md = report.render_verdict(result)
    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)


def main():
    p = argparse.ArgumentParser(prog="hurdle", description="Sector Public Hurdle System")
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hurdle", help="레짐 + 허들 산출")
    h.add_argument("--universe", required=True)
    h.add_argument("--config", default="config/semiconductor.yaml")
    h.set_defaults(fn=cmd_hurdle)
    dl = sub.add_parser("deal", help="딜 YAML 판정")
    dl.add_argument("deal")
    dl.add_argument("--universe", required=True)
    dl.add_argument("--config", default="config/semiconductor.yaml")
    dl.add_argument("--out")
    dl.set_defaults(fn=cmd_deal)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
