from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from io import BytesIO
import logging
from math import pow
import os
from statistics import mean, median
from typing import Final
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

import requests
from typing_extensions import override

from ..models import Ticker
from .dart_accounts import Metric, first_amount, sum_amount
from .dart_http import DartPayload, DartRow, DartTransportError, HttpResponse, HttpSession, default_session

CORP_CODE_URL: Final = "https://opendart.fss.or.kr/api/corpCode.xml"
FINANCIAL_URL: Final = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
ANNUAL_REPORT_CODE: Final = "11011"
LOGGER: Final = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MissingDartApiKey(Exception):
    @override
    def __str__(self) -> str:
        return "DART_API_KEY is required for OpenDART financials"


@dataclass(frozen=True, slots=True)
class DartApiError(Exception):
    status: str
    message: str

    @override
    def __str__(self) -> str:
        return f"OpenDART API error {self.status}: {self.message}"


@dataclass(frozen=True, slots=True)
class DartLine:
    statement: str
    account_id: str
    account_name: str
    amount: float


@dataclass(frozen=True, slots=True)
class CorpEntry:
    corp_code: str
    corp_name: str
    stock_code: str


@dataclass(frozen=True, slots=True)
class FinancialSnapshot:
    revenue: float
    fcf: float
    fcf_margin: float
    roic: float | None
    netdebt_ebitda: float | None


@dataclass(frozen=True, slots=True)
class ComputedFinancials:
    ttm_rev: float
    ttm_fcf: float
    fcf_margin_3y: float
    growth: float
    roic_3y: float
    netdebt_ebitda: float
    rev_cagr_3y: float


@dataclass(frozen=True, slots=True)
class DartClient:
    api_key: str
    session: HttpSession = field(default_factory=default_session)
    base_year: int = field(default_factory=lambda: date.today().year - 1)
    fs_div: str = "CFS"
    timeout: float = 20.0

    def fill_financials(self, tickers: list[Ticker]) -> list[Ticker]:
        if not tickers:
            return []
        corp_index = self._corp_index()
        filled: list[Ticker] = []
        for ticker in tickers:
            if ticker.market != "KR":
                filled.append(ticker)
                continue
            corp = _find_corp(corp_index, ticker.symbol)
            if corp is None:
                LOGGER.warning("DART corp_code missing for %s", ticker.symbol)
                filled.append(ticker)
                continue
            computed = self._computed_financials(corp)
            if computed is None:
                LOGGER.warning("DART financials missing for %s (%s)", ticker.symbol, corp.corp_code)
                filled.append(ticker)
                continue
            filled.append(
                replace(
                    ticker,
                    ttm_rev=computed.ttm_rev,
                    ttm_fcf=computed.ttm_fcf,
                    fcf_margin_3y=computed.fcf_margin_3y,
                    growth=computed.growth,
                    roic_3y=computed.roic_3y,
                    netdebt_ebitda=computed.netdebt_ebitda,
                    rev_cagr_3y=computed.rev_cagr_3y,
                    source="dart",
                )
            )
        return filled

    def _corp_index(self) -> dict[str, CorpEntry]:
        response = self._get(CORP_CODE_URL, {"crtfc_key": self.api_key})
        try:
            entries = _parse_corp_zip(response.content)
        except (BadZipFile, ET.ParseError) as exc:
            raise DartTransportError(detail="invalid corpCode.xml zip") from exc
        index: dict[str, CorpEntry] = {}
        for entry in entries:
            index[_normalize_name(entry.corp_name)] = entry
            if entry.stock_code:
                index[entry.stock_code] = entry
        return index

    def _computed_financials(self, corp: CorpEntry) -> ComputedFinancials | None:
        snapshots = [
            snapshot
            for year in range(self.base_year, self.base_year - 3, -1)
            if (snapshot := self._annual_snapshot(corp, year)) is not None
        ]
        if not snapshots:
            return None
        latest = snapshots[0]
        margins = [snapshot.fcf_margin for snapshot in snapshots if snapshot.revenue > 0]
        roics = [snapshot.roic for snapshot in snapshots if snapshot.roic is not None]
        rev_cagr = _revenue_cagr([snapshot.revenue for snapshot in snapshots])
        return ComputedFinancials(
            ttm_rev=round(latest.revenue, 1),
            ttm_fcf=round(latest.fcf, 1),
            fcf_margin_3y=round(median(margins), 1) if margins else 0.0,
            growth=rev_cagr,
            roic_3y=round(mean(roics), 1) if roics else 0.0,
            netdebt_ebitda=round(latest.netdebt_ebitda, 2) if latest.netdebt_ebitda is not None else 0.0,
            rev_cagr_3y=rev_cagr,
        )

    def _annual_snapshot(self, corp: CorpEntry, year: int) -> FinancialSnapshot | None:
        lines = self._statement_lines(corp, year)
        if not lines:
            return None
        revenue = first_amount(lines, Metric.REVENUE)
        if revenue <= 0:
            return None
        ocf = first_amount(lines, Metric.OCF)
        capex = abs(first_amount(lines, Metric.CAPEX))
        operating_income = first_amount(lines, Metric.OPERATING_INCOME)
        pretax_income = first_amount(lines, Metric.PRETAX_INCOME)
        tax_expense = first_amount(lines, Metric.TAX_EXPENSE)
        cash = first_amount(lines, Metric.CASH)
        equity = first_amount(lines, Metric.EQUITY)
        debt = sum_amount(lines, Metric.DEBT)
        depreciation = sum_amount(lines, Metric.DEPRECIATION)
        fcf = ocf - capex
        net_debt = debt - cash
        ebitda = operating_income + depreciation
        return FinancialSnapshot(
            revenue=revenue,
            fcf=fcf,
            fcf_margin=fcf / revenue * 100,
            roic=_roic(operating_income, tax_expense, pretax_income, equity + net_debt),
            netdebt_ebitda=net_debt / ebitda if ebitda > 0 else None,
        )

    def _statement_lines(self, corp: CorpEntry, year: int) -> list[DartLine]:
        payload = self._get_json(
            FINANCIAL_URL,
            {
                "crtfc_key": self.api_key,
                "corp_code": corp.corp_code,
                "bsns_year": str(year),
                "reprt_code": ANNUAL_REPORT_CODE,
                "fs_div": self.fs_div,
            },
        )
        status = str(payload.get("status", ""))
        if status == "013":
            return []
        if status != "000":
            raise DartApiError(status=status, message=str(payload.get("message", "")))
        rows = payload.get("list", [])
        if not isinstance(rows, list):
            raise DartApiError(status="900", message="OpenDART list payload is not a list")
        return [_parse_line(row) for row in rows]

    def _get_json(self, url: str, params: Mapping[str, str]) -> DartPayload:
        response = self._get(url, params)
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise DartTransportError(detail="invalid JSON response") from exc

    def _get(self, url: str, params: Mapping[str, str]) -> HttpResponse:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DartTransportError(detail=str(exc)) from exc
        return response


def fill_financials(tickers: list[Ticker], api_key: str | None = None) -> list[Ticker]:
    key = api_key or os.environ.get("DART_API_KEY")
    if not key:
        raise MissingDartApiKey()
    return DartClient(api_key=key).fill_financials(tickers)


def _parse_corp_zip(content: bytes) -> tuple[CorpEntry, ...]:
    with ZipFile(BytesIO(content)) as zf:
        xml_name = next(name for name in zf.namelist() if name.lower().endswith(".xml"))
        with zf.open(xml_name) as xml_file:
            root = ET.parse(xml_file).getroot()
    return tuple(
        CorpEntry(
            corp_code=_child_text(node, "corp_code"),
            corp_name=_child_text(node, "corp_name"),
            stock_code=_child_text(node, "stock_code"),
        )
        for node in root.findall("list")
    )


def _child_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    return "" if child is None or child.text is None else child.text.strip()


def _find_corp(index: Mapping[str, CorpEntry], symbol: str) -> CorpEntry | None:
    normalized = _normalize_name(symbol.split(".", maxsplit=1)[0])
    return index.get(normalized) or index.get(symbol[:6])


def _parse_line(row: DartRow) -> DartLine:
    amount = row.get("thstrm_add_amount") or row.get("thstrm_amount") or ""
    return DartLine(
        statement=row.get("sj_div", "").strip(),
        account_id=row.get("account_id", "").strip(),
        account_name=_normalize_name(row.get("account_nm", "")),
        amount=_parse_amount_eok(amount),
    )


def _parse_amount_eok(raw: str) -> float:
    value = raw.strip().replace(",", "")
    if not value or value == "-":
        return 0.0
    negative = value.startswith("(") and value.endswith(")")
    value = value.strip("()")
    try:
        amount = float(value) / 100_000_000
    except ValueError:
        return 0.0
    return -amount if negative else amount


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch.isalnum())


def _roic(operating_income: float, tax_expense: float, pretax_income: float, invested_capital: float) -> float | None:
    if invested_capital <= 0 or operating_income == 0:
        return None
    tax_rate = tax_expense / pretax_income if pretax_income > 0 and tax_expense >= 0 else 0.0
    return operating_income * (1 - tax_rate) / invested_capital * 100


def _revenue_cagr(revenues: Sequence[float]) -> float:
    if len(revenues) < 2 or revenues[0] <= 0 or revenues[-1] <= 0:
        return 0.0
    years = len(revenues) - 1
    growth = (pow(revenues[0] / revenues[-1], 1.0 / years) - 1.0) * 100.0
    return round(growth, 1)
