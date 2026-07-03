from hurdle.models import Ticker
from hurdle.engine.quality import evaluate
from hurdle.engine.hurdle import compute

CFG = {"engine": {"consensus_haircut": 0.15, "terminal_growth": 0.03, "growth_cap": 0.30, "fcf_mode": "normalized"},
       "quality": {"roic_min": 15, "fcf_margin_min": 10, "netdebt_ebitda_max": 2.0},
       "premium": {"illiquidity": 0.05, "info_governance": 0.03, "execution_dilution": 0.02}}


def _t(name, mcap, rev, margin, roic=20, nd=0.5, cagr=10, ttm_fcf=None):
    return Ticker(symbol=name, market="KR", ccy="KRW", sector="semi",
                  mcap=mcap, ttm_rev=rev, ttm_fcf=ttm_fcf if ttm_fcf is not None else rev * margin / 100,
                  fcf_margin_3y=margin, growth=10, roic_3y=roic, netdebt_ebitda=nd, rev_cagr_3y=cagr)


def test_valuetrap_excluded_from_hurdle():
    # 싸지만(r* 최고) 품질 미달인 종목이 허들에 못 들어가야 한다
    rows = [_t("trap", 500, 1000, 20, roic=5), _t("a", 2000, 1000, 20),
            _t("b", 2500, 1000, 20), _t("c", 3000, 1000, 20)]
    ev = [(t, evaluate(t, CFG)) for t in rows]
    H = compute(ev, CFG)
    assert "trap" not in H.top3
    assert H.pool_count == 3


def test_missing_financials_never_pass():
    t = Ticker(symbol="empty", market="KR", ccy="KRW", sector="semi", mcap=1000)
    v = evaluate(t, CFG)
    assert not v.quality_pass and v.r_flag == "입력부족"


def test_cycle_peak_guard():
    # V4: TTM FCF가 정규화 FCF 1.5배 초과 -> 태그
    t = _t("peak", 2000, 1000, 20, ttm_fcf=400)
    assert evaluate(t, CFG).cycle_peak


def test_hurdle_formula():
    rows = [_t("a", 1500, 1000, 20), _t("b", 1600, 1000, 20), _t("c", 1700, 1000, 20)]
    ev = [(t, evaluate(t, CFG)) for t in rows]
    H = compute(ev, CFG)
    assert H.hurdle is not None
    assert abs(H.hurdle - (H.basket + 0.10)) < 1e-9
