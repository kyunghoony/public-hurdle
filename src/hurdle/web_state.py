from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, TypedDict

from .cli import read_pool, read_universe, write_universe
from .config import load_config
from .engine import hurdle as hurdle_mod
from .engine import quality, regime
from .models import Ticker, Valuation
from .providers import yahoo
from .refresh import merge_universe


@dataclass(frozen=True, slots=True)
class WebPaths:
    universe: Path
    pool: Path
    config: Path


class BrowserSummary(TypedDict):
    count: int
    financialCount: int
    qualityPassCount: int
    totalMcap: int | float


class BrowserRegime(TypedDict):
    tag: str
    ret3m: float | None
    off52w: float | None
    n: int


class BrowserHurdle(TypedDict):
    basket: float | None
    premium: float
    hurdle: float | None
    top3: list[str]


class BrowserRow(TypedDict):
    ticker: str
    market: str
    ccy: str
    sector: str
    subsector: str
    mcap: int | float
    ttmRev: int | float
    ttmFCF: int | float
    margin3y: int | float
    growth: int | float
    roic: int | float
    ndEbitda: int | float
    cagr: int | float
    ret1m: float | None
    ret3m: float | None
    ret6m: float | None
    off52w: float | None
    qualityPass: bool
    qualityFails: list[str]
    rStar: float | None
    rFlag: str | None
    gStar: float | None
    cyclePeak: bool


class RefreshSummary(TypedDict):
    preservedCount: int
    oldFinancialCount: int
    skipped: list[str]


class BrowserState(TypedDict, total=False):
    summary: BrowserSummary
    regime: BrowserRegime
    hurdle: BrowserHurdle
    sectors: list[str]
    rows: list[BrowserRow]
    refresh: RefreshSummary


ConfigValue: TypeAlias = str | int | float | bool | list[float] | dict[str, "ConfigValue"]
Config: TypeAlias = dict[str, ConfigValue]
UniverseFetcher: TypeAlias = Callable[[list[yahoo.PoolRow], Config, int], list[Ticker]]


def _number(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return round(value, 4)


def _optional_number(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _browser_row(ticker: Ticker, valuation: Valuation) -> BrowserRow:
    return {
        "ticker": ticker.symbol,
        "market": ticker.market,
        "ccy": ticker.ccy,
        "sector": ticker.sector,
        "subsector": ticker.subsector or "",
        "mcap": _number(ticker.mcap),
        "ttmRev": _number(ticker.ttm_rev),
        "ttmFCF": _number(ticker.ttm_fcf),
        "margin3y": _number(ticker.fcf_margin_3y),
        "growth": _number(ticker.growth),
        "roic": _number(ticker.roic_3y),
        "ndEbitda": _number(ticker.netdebt_ebitda),
        "cagr": _number(ticker.rev_cagr_3y),
        "ret1m": _optional_number(ticker.ret_1m),
        "ret3m": _optional_number(ticker.ret_3m),
        "ret6m": _optional_number(ticker.ret_6m),
        "off52w": _optional_number(ticker.off_52w_high),
        "qualityPass": valuation.quality_pass,
        "qualityFails": valuation.quality_fails,
        "rStar": _optional_number(valuation.r_star),
        "rFlag": valuation.r_flag,
        "gStar": _optional_number(valuation.g_star),
        "cyclePeak": valuation.cycle_peak,
    }


def _missing_entries(pool_path: Path) -> list[str]:
    missing_path = pool_path.with_name("missing.log")
    if not missing_path.exists():
        return []
    return [line.strip() for line in missing_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_state(paths: WebPaths) -> BrowserState:
    rows = read_universe(str(paths.universe))
    cfg = load_config(str(paths.config))
    evaluated = [(ticker, quality.evaluate(ticker, cfg)) for ticker in rows]
    reg = regime.classify(rows, cfg)
    hurdle = hurdle_mod.compute(evaluated, cfg)
    sectors = sorted({ticker.sector for ticker in rows if ticker.sector})
    return {
        "summary": {
            "count": len(rows),
            "financialCount": sum(1 for ticker in rows if ticker.ttm_rev > 0),
            "qualityPassCount": hurdle.pool_count,
            "totalMcap": _number(sum(ticker.mcap for ticker in rows)),
        },
        "regime": {
            "tag": reg.tag,
            "ret3m": _optional_number(reg.ret_3m),
            "off52w": _optional_number(reg.off_52w),
            "n": reg.n,
        },
        "hurdle": {
            "basket": _optional_number(hurdle.basket),
            "premium": _number(hurdle.premium),
            "hurdle": _optional_number(hurdle.hurdle),
            "top3": hurdle.top3,
        },
        "sectors": sectors,
        "rows": [_browser_row(ticker, valuation) for ticker, valuation in evaluated],
    }


def refresh_state(paths: WebPaths, top_n: int, fetcher: UniverseFetcher = yahoo.fetch_universe) -> BrowserState:
    pool = read_pool(str(paths.pool))
    old = read_universe(str(paths.universe)) if paths.universe.exists() else []
    old_financial_symbols = {ticker.symbol for ticker in old if ticker.ttm_rev > 0}
    fresh = fetcher(pool, load_config(str(paths.config)), top_n)
    write_universe(str(paths.universe), merge_universe(fresh, old))
    state = build_state(paths)
    state["refresh"] = {
        "preservedCount": sum(1 for ticker in fresh if ticker.symbol in old_financial_symbols),
        "oldFinancialCount": len(old_financial_symbols),
        "skipped": _missing_entries(paths.pool),
    }
    return state
