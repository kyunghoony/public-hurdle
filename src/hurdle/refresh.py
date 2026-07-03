from typing import Final, TypedDict

from .models import Ticker

CSV_COLUMNS: Final[tuple[str, ...]] = (
    "ticker",
    "market",
    "ccy",
    "sector",
    "subsector",
    "mcap",
    "ttmRev",
    "ttmFCF",
    "margin3y",
    "growth",
    "roic",
    "ndEbitda",
    "cagr",
    "ret1m",
    "ret3m",
    "ret6m",
    "off52w",
)
FINANCIAL_COLUMNS: Final[tuple[str, ...]] = (
    "ttmRev",
    "ttmFCF",
    "margin3y",
    "growth",
    "roic",
    "ndEbitda",
    "cagr",
)


class UniverseRow(TypedDict):
    ticker: str
    market: str
    ccy: str
    sector: str
    subsector: str
    mcap: str
    ttmRev: str
    ttmFCF: str
    margin3y: str
    growth: str
    roic: str
    ndEbitda: str
    cagr: str
    ret1m: str
    ret3m: str
    ret6m: str
    off52w: str


def _format_number(value: float) -> str:
    if abs(value) < 1e-12:
        return "0"
    if value.is_integer():
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return ""
    return _format_number(value)


def _financials(old: Ticker | None) -> dict[str, str]:
    if old is None or old.ttm_rev <= 0:
        return {column: "" for column in FINANCIAL_COLUMNS}
    return {
        "ttmRev": _format_number(old.ttm_rev),
        "ttmFCF": _format_number(old.ttm_fcf),
        "margin3y": _format_number(old.fcf_margin_3y),
        "growth": _format_number(old.growth),
        "roic": _format_number(old.roic_3y),
        "ndEbitda": _format_number(old.netdebt_ebitda),
        "cagr": _format_number(old.rev_cagr_3y),
    }


def merge_universe(fresh: list[Ticker], old: list[Ticker]) -> list[UniverseRow]:
    old_by_symbol = {ticker.symbol: ticker for ticker in old}
    rows: list[UniverseRow] = []
    for ticker in fresh:
        old_ticker = old_by_symbol.get(ticker.symbol)
        base = old_ticker if old_ticker is not None else ticker
        row: UniverseRow = {
            "ticker": ticker.symbol,
            "market": base.market,
            "ccy": base.ccy,
            "sector": base.sector,
            "subsector": base.subsector or "",
            "mcap": _format_number(ticker.mcap),
            "ttmRev": "",
            "ttmFCF": "",
            "margin3y": "",
            "growth": "",
            "roic": "",
            "ndEbitda": "",
            "cagr": "",
            "ret1m": _format_optional_number(ticker.ret_1m),
            "ret3m": _format_optional_number(ticker.ret_3m),
            "ret6m": _format_optional_number(ticker.ret_6m),
            "off52w": _format_optional_number(ticker.off_52w_high),
        }
        row.update(_financials(old_ticker))
        rows.append(row)
    return rows
