"""프로바이더 인터페이스 — 새 소스는 이 규약만 지키면 엔진 수정 없이 붙는다."""
from typing import Protocol
from ..models import Ticker


class MarketDataProvider(Protocol):
    def fetch_universe(self, pool: list[dict], cfg: dict) -> list[Ticker]:
        """후보 풀 -> 시총/모멘텀 채워진 Ticker 리스트 (재무는 별도 프로바이더)."""
        ...


class FinancialsProvider(Protocol):
    def fill_financials(self, tickers: list[Ticker]) -> list[Ticker]:
        """ttm_rev/ttm_fcf/margins/roic/netdebt/cagr 채움. 결측 시 0 유지 + 로그 (imputation 금지)."""
        ...
