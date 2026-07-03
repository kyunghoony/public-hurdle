"""CLI — python -m hurdle.cli <command>"""
import argparse
import csv
from pathlib import Path
from .config import load_config
from .models import Ticker
from .engine import quality, regime, hurdle as hurdle_mod
from . import deal as deal_mod
from . import report
from .providers import dart, yahoo
from .providers.dart import DartApiError, MissingDartApiKey
from .providers.dart_http import DartTransportError
from .refresh import CSV_COLUMNS, UniverseRow, merge_financials, merge_universe

COLS = list(CSV_COLUMNS)


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


def read_pool(path: str) -> list[yahoo.PoolRow]:
    out: list[yahoo.PoolRow] = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            out.append(
                {
                    "code": row["code"],
                    "suffix": row["suffix"],
                    "name": row["name"],
                    "sector": row["sector"],
                    "subsector": row.get("subsector", ""),
                }
            )
    return out


def write_universe(path: str, rows: list[UniverseRow]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLS)
        writer.writeheader()
        writer.writerows(rows)


def _missing_entries(pool_path: str) -> list[str]:
    missing_path = Path(pool_path).with_name("missing.log")
    if not missing_path.exists():
        return []
    return [line.strip() for line in missing_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cmd_fetch(args):
    pool = read_pool(args.pool)
    old = read_universe(args.out) if Path(args.out).exists() else []
    fresh = yahoo.fetch_universe(pool, {}, top_n=args.top)
    rows = merge_universe(fresh, old)
    write_universe(args.out, rows)
    old_financial_symbols = {ticker.symbol for ticker in old if ticker.ttm_rev > 0}
    preserved_count = sum(1 for ticker in fresh if ticker.symbol in old_financial_symbols)
    missing = _missing_entries(args.pool)
    print(f"종목 수: {len(rows)}")
    print(f"재무 보존 건수: {preserved_count}")
    print("스킵 목록: " + (", ".join(missing) if missing else "없음"))


def cmd_dart_fill(args):
    old = read_universe(args.universe)
    old_financial_count = sum(1 for ticker in old if ticker.ttm_rev > 0)
    try:
        filled = dart.fill_financials(old)
    except MissingDartApiKey as exc:
        raise SystemExit("오류: DART_API_KEY 환경변수가 필요합니다.") from exc
    except (DartApiError, DartTransportError) as exc:
        raise SystemExit(f"오류: {exc}") from exc
    rows = merge_financials(filled, old)
    write_universe(args.out or args.universe, rows)
    financial_count = sum(1 for row in rows if row["ttmRev"])
    missing = [row["ticker"] for row in rows if not row["ttmRev"]]
    print(f"종목 수: {len(rows)}")
    print(f"기존 재무 입력 건수: {old_financial_count}")
    print(f"DART 후 재무 입력 건수: {financial_count}")
    print("재무 미입력: " + (", ".join(missing) if missing else "없음"))


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
    fetch = sub.add_parser("fetch", help="KR 유니버스 시세/모멘텀 갱신")
    fetch.add_argument("--pool", required=True)
    fetch.add_argument("--out", required=True)
    fetch.add_argument("--top", type=int, default=100)
    fetch.set_defaults(fn=cmd_fetch)
    dart_fill = sub.add_parser("dart-fill", help="OpenDART로 재무 컬럼 채움")
    dart_fill.add_argument("--universe", required=True)
    dart_fill.add_argument("--out")
    dart_fill.set_defaults(fn=cmd_dart_fill)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
