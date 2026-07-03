"""허들 산출 — Hurdle = mean(top-3 r*, 품질 통과) + 프리미엄 (+ HOT 레짐 가산).

top-3 평균인 이유: max는 한 종목 미스프라이싱 노이즈에 휘둘리고,
median은 너무 낮아 허들 기능을 상실한다.
'지금 당장 살 수 있는 최선의 바스켓'이 진짜 기회비용.
"""
from ..models import Ticker, Valuation, HurdleResult


def compute(rows: list[tuple[Ticker, Valuation]], cfg: dict) -> HurdleResult:
    p = cfg["premium"]
    premium = p["illiquidity"] + p["info_governance"] + p["execution_dilution"]
    pool = [(t, v) for t, v in rows if v.quality_pass and v.r_star is not None]
    pool.sort(key=lambda x: -x[1].r_star)
    top3 = pool[:3]
    basket = sum(v.r_star for _, v in top3) / 3 if len(top3) >= 3 else None
    return HurdleResult(
        basket=basket, premium=premium,
        hurdle=(basket + premium) if basket is not None else None,
        top3=[t.symbol for t, _ in top3], pool_count=len(pool),
    )
