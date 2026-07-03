"""V3: 골든 라운드트립 + 단조성 — 통과 못 하면 다음 단계 진행 금지."""
from hurdle.engine.dcf import pv_at, solve_irr, solve_implied_growth

CFG = {"engine": {"consensus_haircut": 0.15, "terminal_growth": 0.03, "growth_cap": 0.30}}


def test_golden_roundtrip():
    # 알려진 r로 PV를 만들고, 솔버가 그 r을 복원하는지 (±2bp)
    for r_true in (0.06, 0.10, 0.18):
        g12 = min(0.20 * 0.85, 0.30)
        mcap = pv_at(r_true, 100.0, g12, 0.03)
        r, flag = solve_irr(mcap, 100.0, 0.20, CFG)
        assert flag is None
        assert abs(r - r_true) < 2e-4


def test_monotonicity():
    # 가격 +10% -> r* 엄격 감소
    g12 = 0.10 * 0.85
    base = pv_at(0.10, 100.0, g12, 0.03)
    r1, _ = solve_irr(base, 100.0, 0.10, CFG)
    r2, _ = solve_irr(base * 1.10, 100.0, 0.10, CFG)
    assert r2 < r1


def test_input_guard():
    assert solve_irr(0, 100, 0.1, CFG) == (None, "입력부족")
    assert solve_irr(1000, 0, 0.1, CFG) == (None, "입력부족")


def test_implied_growth_direction():
    # 비싼 가격일수록 내재성장률이 높아야 한다
    g_cheap = solve_implied_growth(1000.0, 100.0, CFG)
    g_rich = solve_implied_growth(3000.0, 100.0, CFG)
    assert g_rich > g_cheap
