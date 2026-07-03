"""품질 게이트 — 허들은 '실제로 살 만한' quality compounder로만 구성한다.

밸류트랩이 허들을 낮추면 시스템 전체가 오염된다.
재무 미입력(invalid)은 자동 탈락 — 조용한 imputation 절대 금지.
"""
from ..models import Ticker, Valuation
from .dcf import solve_irr, solve_implied_growth


def evaluate(t: Ticker, cfg: dict) -> Valuation:
    q = cfg["quality"]
    fcf0 = t.ttm_rev * t.fcf_margin_3y / 100          # normalized FCF
    valid = t.mcap > 0 and t.ttm_rev > 0 and t.fcf_margin_3y > 0
    cycle_peak = valid and t.ttm_fcf > 1.5 * fcf0     # V4 사이클 가드
    r_star, r_flag = solve_irr(t.mcap, fcf0, t.growth / 100, cfg) if valid else (None, "입력부족")
    g_star = solve_implied_growth(t.mcap, fcf0, cfg) if valid else None
    fails = []
    if not valid:
        fails.append("재무 미입력")
    else:
        if t.roic_3y < q["roic_min"]:
            fails.append(f"ROIC<{q['roic_min']}%")
        if t.fcf_margin_3y < q["fcf_margin_min"]:
            fails.append(f"FCF마진<{q['fcf_margin_min']}%")
        if t.netdebt_ebitda > q["netdebt_ebitda_max"]:
            fails.append(f"순부채/EBITDA>{q['netdebt_ebitda_max']}x")
        if t.rev_cagr_3y <= 0:
            fails.append("역성장")
    return Valuation(r_star=r_star, r_flag=r_flag, g_star=g_star, fcf0=fcf0,
                     cycle_peak=cycle_peak, quality_pass=(valid and not fails),
                     quality_fails=fails)
