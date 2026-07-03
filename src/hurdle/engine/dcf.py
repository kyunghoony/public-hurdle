"""Reverse DCF 엔진 — FinanceToolkit 철학 차용: 모든 공식은 투명한 순수 함수.

같은 지표가 소스마다 다른 이유는 계산법이 숨겨져 있기 때문이다
(MSFT PER가 제공자에 따라 28.9~34.4). 우리는 공식을 코드에 그대로 노출한다.

모델:
  MarketCap = SUM_{t=1..5} FCF_t/(1+r)^t + TV/(1+r)^5
  TV = FCF_5 x (1+gT) / (r - gT)
  성장 경로: y1~2 = g12(컨센서스 x (1-haircut), cap 30%), y3~5 선형 fade -> gT
  FCF_0 = TTM매출 x 3yr 중위 FCF마진  (normalized — 사이클 왜곡 제거)
"""


def fcf_path(fcf0: float, g12: float, g_t: float) -> list[float]:
    growth = [g12, g12]
    for k in range(1, 4):                      # y3~5: 선형 fade
        growth.append(g12 + (g_t - g12) * k / 3)
    path, f = [], fcf0
    for g in growth:
        f *= 1 + g
        path.append(f)
    return path


def pv_at(r: float, fcf0: float, g12: float, g_t: float) -> float:
    if r <= g_t + 0.001:
        return float("inf")
    path = fcf_path(fcf0, g12, g_t)
    pv = sum(path[t] / (1 + r) ** (t + 1) for t in range(5))
    tv = path[4] * (1 + g_t) / (r - g_t)
    return pv + tv / (1 + r) ** 5


def solve_irr(mcap: float, fcf0: float, growth_raw: float, cfg: dict) -> tuple[float | None, str | None]:
    """r* : 현재가에 내재된 기대수익률. bisection (PV는 r에 대해 단조감소)."""
    if mcap <= 0 or fcf0 <= 0:
        return None, "입력부족"
    e = cfg["engine"]
    g12 = min(growth_raw * (1 - e["consensus_haircut"]), e["growth_cap"])
    g_t = e["terminal_growth"]
    lo, hi = g_t + 0.005, 0.60
    if pv_at(lo, fcf0, g12, g_t) < mcap:
        return lo, "≤"      # 극단 고평가 — 하한 클램프
    if pv_at(hi, fcf0, g12, g_t) > mcap:
        return hi, "≥"      # 극단 저평가 — 상한 클램프
    for _ in range(100):
        mid = (lo + hi) / 2
        diff = pv_at(mid, fcf0, g12, g_t) - mcap
        if abs(diff) < mcap * 1e-7:
            return mid, None
        if diff > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, None


def solve_implied_growth(mcap: float, fcf0: float, cfg: dict, r: float = 0.10) -> float | None:
    """g* : r=10% 고정 시 내재성장률 — 시장이 가격에 깔아놓은 기대 (haircut 미적용)."""
    if mcap <= 0 or fcf0 <= 0:
        return None
    g_t = cfg["engine"]["terminal_growth"]
    lo, hi = -0.30, 0.80
    f = lambda g: pv_at(r, fcf0, g, g_t) - mcap   # g에 대해 단조증가
    if f(lo) > 0:
        return lo
    if f(hi) < 0:
        return hi
    for _ in range(100):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
