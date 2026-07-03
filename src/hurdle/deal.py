"""딜 평가 — TradingAgents 패턴 차용: 판정은 구조화된 설명가능 로그로 남긴다.

산출물은 숫자가 아니라 반증 가능한 문장:
"본 딜은 [바스켓] 대비 연 X%p 초과수익 가정 — 근거는?"
"""
import yaml
from .models import HurdleResult, Regime


def load_deal(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def evaluate_deal(deal: dict, H: HurdleResult, regime: Regime, cfg: dict) -> dict:
    stake = deal["investment"] / (deal["entry_pre"] + deal["investment"])
    regime_add = cfg["regime"]["hot_premium_add"] if regime.tag == "HOT" else 0.0
    hurdle_adj = H.hurdle + regime_add if H.hurdle is not None else None

    scenarios = {}
    for name, s in deal["exit_scenarios"].items():
        proceeds = s["rev"] * s["mult"] * stake * (1 - deal["dilution_to_exit"])
        irr = (proceeds / deal["investment"]) ** (1 / deal["exit_year"]) - 1
        scenarios[name] = {"proceeds": proceeds, "irr": irr, "moic": proceeds / deal["investment"]}

    # HOT이면 base 배수 -25% 감액 시나리오 강제 (피크 멀티플 앵커링 점검)
    if regime.tag == "HOT":
        b = deal["exit_scenarios"]["base"]
        proceeds = b["rev"] * b["mult"] * 0.75 * stake * (1 - deal["dilution_to_exit"])
        scenarios["base_haircut25"] = {"proceeds": proceeds,
                                       "irr": (proceeds / deal["investment"]) ** (1 / deal["exit_year"]) - 1,
                                       "moic": proceeds / deal["investment"]}

    verdict, diff = None, None
    if hurdle_adj is not None:
        diff = scenarios["base"]["irr"] - hurdle_adj
        band = cfg["verdict"]["borderline_band"]
        verdict = "PASS" if diff >= 0 else ("BORDERLINE" if diff >= -band else "FAIL")

    return {"deal": deal["name"], "stake": stake, "scenarios": scenarios,
            "hurdle_base": H.hurdle, "regime_tag": regime.tag, "regime_add": regime_add,
            "hurdle_adj": hurdle_adj, "verdict": verdict, "diff": diff,
            "basket": H.top3, "basket_return": H.basket, "premium": H.premium}
