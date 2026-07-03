"""레짐 모니터 — 모멘텀은 매력도 신호가 아니라 리스크 컨텍스트.

HOT을 매력도 점수로 쓰면 밸류에이션 엔진과 반대말을 하게 되고,
사람은 자기 딜을 지지하는 숫자를 골라 쓰게 된다.
HOT은 exit 배수 앵커링 리스크 -> 프리미엄 가산 트리거로만 작동한다.

블로우오프 조항: 3M이 극단적이면(기본 +40%) 고점比 조정 중이어도 HOT.
2026-07 실데이터 캘리브레이션에서 나온 룰 — 반도체 3M +111%가
최근 고점 -18% 조정 때문에 NEUTRAL로 읽히는 것을 방지.
"""
from ..models import Ticker, Regime


def _w_eok(t: Ticker, fx: float) -> float:
    return t.mcap * fx / 100 if t.ccy == "USD" else t.mcap   # $M -> 억원


def _cap_weighted(rows: list[Ticker], field: str, fx: float) -> float | None:
    valid = [t for t in rows if getattr(t, field) is not None and t.mcap > 0]
    tw = sum(_w_eok(t, fx) for t in valid)
    if not tw:
        return None
    return sum(_w_eok(t, fx) * getattr(t, field) for t in valid) / tw


def classify(rows: list[Ticker], cfg: dict) -> Regime:
    rg, fx = cfg["regime"], cfg["universe"]["fx_krw_usd"]
    with_mom = [t for t in rows if t.ret_3m is not None and t.off_52w_high is not None and t.mcap > 0]
    if len(with_mom) < rg["min_names"]:
        return Regime(tag="표본부족", ret_3m=None, off_52w=None, n=len(with_mom))
    r3 = _cap_weighted(with_mom, "ret_3m", fx)
    off = _cap_weighted(with_mom, "off_52w_high", fx)
    tag = "NEUTRAL"
    if (r3 >= rg["hot_ret3m"] and off >= rg["hot_off52"]) or r3 >= rg["hot_blowoff_ret3m"]:
        tag = "HOT"
    elif r3 < rg["cold_ret3m"] and off <= rg["cold_off52"]:
        tag = "COLD"
    return Regime(tag=tag, ret_3m=r3, off_52w=off, n=len(with_mom))
