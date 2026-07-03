from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from typing import TypeAlias
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from hurdle.models import Ticker
from hurdle.providers.dart import DartClient, MissingDartApiKey, fill_financials
from hurdle.providers.dart_http import DartPayload, DartRow

StatementKey: TypeAlias = tuple[str, str, str, str]
Statements: TypeAlias = Mapping[StatementKey, list[DartRow]]


class FakeResponse:
    _payload: DartPayload
    content: bytes

    def __init__(self, *, payload: DartPayload | None = None, content: bytes = b"") -> None:
        self._payload = payload or {"status": "000", "message": "정상", "list": []}
        self.content = content

    def json(self) -> DartPayload:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    statements: Statements
    calls: list[tuple[str, Mapping[str, str], float]]

    def __init__(self, statements: Statements) -> None:
        self.statements = statements
        self.calls = []

    def get(self, url: str, *, params: Mapping[str, str], timeout: float) -> FakeResponse:
        self.calls.append((url, params, timeout))
        if url.endswith("/corpCode.xml"):
            return FakeResponse(content=_corp_zip())
        key = (params["corp_code"], params["bsns_year"], params["reprt_code"], params["fs_div"])
        return FakeResponse(payload={"status": "000", "message": "정상", "list": self.statements[key]})


def _corp_zip() -> bytes:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126380</corp_code>
    <corp_name>삼성전자</corp_name>
    <corp_eng_name>SAMSUNG ELECTRONICS</corp_eng_name>
    <stock_code>005930</stock_code>
    <modify_date>20260101</modify_date>
  </list>
</result>
"""
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as zf:
        zf.writestr("CORPCODE.xml", xml)
    return out.getvalue()


def _amount(value: float) -> str:
    return f"{round(value * 100_000_000):,}"


def _line(sj_div: str, account_id: str, account_nm: str, value: float) -> DartRow:
    return {
        "sj_div": sj_div,
        "account_id": account_id,
        "account_nm": account_nm,
        "thstrm_amount": _amount(value),
        "thstrm_add_amount": _amount(value),
        "frmtrm_amount": "",
        "frmtrm_add_amount": "",
        "bfefrmtrm_amount": "",
    }


def _statement(revenue: float, fcf_parts: tuple[float, float], operating_income: float) -> list[DartRow]:
    ocf, capex = fcf_parts
    return [
        _line("IS", "ifrs-full_Revenue", "매출액", revenue),
        _line("IS", "dart_OperatingIncomeLoss", "영업이익", operating_income),
        _line("IS", "ifrs-full_ProfitLossBeforeTax", "법인세비용차감전순이익", 100),
        _line("IS", "ifrs-full_IncomeTaxExpenseContinuingOperations", "법인세비용", 20),
        _line("CF", "ifrs-full_CashFlowsFromUsedInOperatingActivities", "영업활동현금흐름", ocf),
        _line("CF", "ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "유형자산의 취득", -capex),
        _line("CF", "ifrs-full_DepreciationAndAmortisationExpense", "감가상각비", 20),
        _line("BS", "ifrs-full_Equity", "자본총계", 500),
        _line("BS", "ifrs-full_CashAndCashEquivalents", "현금및현금성자산", 50),
        _line("BS", "ifrs-full_ShorttermBorrowings", "단기차입금", 40),
        _line("BS", "ifrs-full_LongtermBorrowings", "장기차입금", 60),
    ]


def test_fill_financials_maps_opendart_annual_reports_to_ticker_metrics():
    # Given: three annual OpenDART full financial statements with mapped accounts.
    statements: dict[StatementKey, list[DartRow]] = {
        ("00126380", "2025", "11011", "CFS"): _statement(1000, (200, 50), 180),
        ("00126380", "2024", "11011", "CFS"): _statement(900, (180, 40), 160),
        ("00126380", "2023", "11011", "CFS"): _statement(800, (160, 40), 140),
    }
    client = DartClient(api_key="x" * 40, session=FakeSession(statements), base_year=2025)
    ticker = Ticker(symbol="삼성전자", market="KR", ccy="KRW", sector="반도체")

    # When: the provider fills financials from OpenDART.
    [filled] = client.fill_financials([ticker])

    # Then: metrics are converted to engine units and no silent imputation is used.
    assert filled.ttm_rev == 1000
    assert filled.ttm_fcf == 150
    assert filled.fcf_margin_3y == pytest.approx(15.0)
    assert filled.rev_cagr_3y == pytest.approx(11.8)
    assert filled.growth == filled.rev_cagr_3y
    assert filled.roic_3y == pytest.approx(23.3)
    assert filled.netdebt_ebitda == pytest.approx(0.25)
    assert filled.source == "dart"
    assert ticker.ttm_rev == 0


def test_fill_financials_keeps_zeroes_when_corp_code_is_missing():
    # Given: a KR ticker not found in DART's corporation code list.
    statements: dict[StatementKey, list[DartRow]] = {}
    client = DartClient(api_key="x" * 40, session=FakeSession(statements), base_year=2025)
    ticker = Ticker(symbol="미등록회사", market="KR", ccy="KRW", sector="반도체")

    # When: the provider cannot map it to a DART corp_code.
    [filled] = client.fill_financials([ticker])

    # Then: missing financials stay zero and the source is not overwritten.
    assert filled == ticker


def test_fill_financials_requires_dart_api_key(monkeypatch: pytest.MonkeyPatch):
    # Given: no explicit key and no DART_API_KEY environment variable.
    monkeypatch.delenv("DART_API_KEY", raising=False)

    # When / Then: the public provider boundary reports a typed configuration error.
    with pytest.raises(MissingDartApiKey):
        _ = fill_financials([])
