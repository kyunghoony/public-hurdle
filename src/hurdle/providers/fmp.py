"""FMP 프로바이더 (US 재무) — FinanceToolkit 패턴: FMP 우선, 실패 시 명시적 폴백.

TODO(v0.2): /api/v3/income-statement, /cash-flow-statement, /balance-sheet-statement
-> ttm_rev, ttm_fcf(OCF-capex), 3yr 중위 FCF마진, ROIC, netdebt/EBITDA, 3yr CAGR.
환경변수 FMP_API_KEY. 결측 필드는 0 유지 + 로그 (조용한 imputation 금지 — V2).
"""


def fill_financials(tickers, api_key: str | None = None):
    raise NotImplementedError("v0.2 — CLAUDE.md의 다음 작업 목록 참조")
