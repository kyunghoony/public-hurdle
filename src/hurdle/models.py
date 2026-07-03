"""표준화 데이터 모델 — OpenBB 패턴 차용.

프로바이더(Yahoo/FMP/DART)가 무엇이든 이 모델로 변환된 뒤에만
엔진에 진입한다. 엔진은 데이터 출처를 모른다.
"""
from dataclasses import dataclass, field


@dataclass
class Ticker:
    symbol: str            # 표시명 (한글명 or 티커)
    market: str            # "US" | "KR"
    ccy: str               # "USD" | "KRW"
    sector: str
    subsector: str | None = None   # 반도체: equip/mat/chip/osat
    # 시장 데이터 (단위: USD=$M, KRW=억원)
    mcap: float = 0.0
    # 재무 (없으면 0 → invalid 처리, 절대 조용히 imputation 하지 않는다)
    ttm_rev: float = 0.0
    ttm_fcf: float = 0.0
    fcf_margin_3y: float = 0.0     # %
    growth: float = 0.0            # % 컨센서스 y1~2 (fallback: 3yr CAGR)
    roic_3y: float = 0.0           # %
    netdebt_ebitda: float = 0.0    # x
    rev_cagr_3y: float = 0.0       # %
    # 모멘텀 (레짐용, %). None = 미수집 → 레짐 표본에서 제외.
    ret_1m: float | None = None
    ret_3m: float | None = None
    ret_6m: float | None = None
    off_52w_high: float | None = None
    source: str = "manual"


@dataclass
class Valuation:
    r_star: float | None       # 내재 기대수익률
    r_flag: str | None         # "≤" / "≥" / "입력부족"
    g_star: float | None       # r=10% 고정 시 내재성장률
    fcf0: float                # 정규화 FCF
    cycle_peak: bool           # V4: TTM FCF > 1.5 x 정규화 FCF
    quality_pass: bool
    quality_fails: list[str] = field(default_factory=list)


@dataclass
class Regime:
    tag: str                   # HOT | NEUTRAL | COLD | 표본부족
    ret_3m: float | None
    off_52w: float | None
    n: int


@dataclass
class HurdleResult:
    basket: float | None       # top-3 평균 r*
    premium: float
    hurdle: float | None       # basket + premium
    top3: list[str] = field(default_factory=list)
    pool_count: int = 0
