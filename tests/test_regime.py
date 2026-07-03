from hurdle.models import Ticker
from hurdle.engine.regime import classify

CFG = {"universe": {"fx_krw_usd": 1390},
       "regime": {"hot_ret3m": 15, "hot_off52": -10, "hot_blowoff_ret3m": 40,
                  "cold_ret3m": 0, "cold_off52": -25, "min_names": 2, "hot_premium_add": 0.025}}


def _t(mcap, r3, off):
    return Ticker(symbol="x", market="KR", ccy="KRW", sector="s", mcap=mcap, ret_3m=r3, off_52w_high=off)


def test_hot_standard():
    assert classify([_t(100, 20, -5), _t(100, 18, -8)], CFG).tag == "HOT"


def test_hot_blowoff_overrides_drawdown():
    # 3M +100%면 고점比 -20% 조정 중이어도 HOT (2026-07 반도체 캘리브레이션)
    assert classify([_t(100, 100, -20), _t(100, 90, -18)], CFG).tag == "HOT"


def test_cold():
    assert classify([_t(100, -5, -30), _t(100, -8, -28)], CFG).tag == "COLD"


def test_insufficient_sample():
    assert classify([_t(100, 50, -5)], CFG).tag == "표본부족"
