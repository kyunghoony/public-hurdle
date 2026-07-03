from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Final, TypedDict

from curl_cffi import requests

from ..models import Ticker

UA: Final = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36"
}
QUOTE_FIELDS: Final = "shortName,marketCap,fiftyTwoWeekHigh,regularMarketPrice,quoteType"


class PoolRow(TypedDict):
    code: str
    suffix: str
    name: str
    sector: str
    subsector: str


class Momentum(TypedDict, total=False):
    ret_1m: float
    ret_3m: float
    ret_6m: float


@dataclass(frozen=True, slots=True)
class RankedQuote:
    symbol: str
    pool_row: PoolRow
    mcap_eok: float
    off_52w_high: float | None


def _session() -> tuple[requests.Session, str]:
    s = requests.Session(impersonate="chrome120", headers=UA)
    s.get("https://fc.yahoo.com", timeout=10)
    crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10).text.strip()
    return s, crumb


def _momentum(s: requests.Session, sym: str) -> Momentum:
    for _ in range(2):
        try:
            r = s.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                params={"range": "1y", "interval": "1d"},
                timeout=15,
            )
            if r.status_code == 429:
                time.sleep(2.5)
                continue
            closes = [c for c in r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
            if len(closes) < 130:
                return {}
            last = closes[-1]
            return {
                "ret_1m": round((last / closes[-22] - 1) * 100, 1),
                "ret_3m": round((last / closes[-64] - 1) * 100, 1),
                "ret_6m": round((last / closes[-127] - 1) * 100, 1),
            }
        except (KeyError, IndexError, TypeError, requests.RequestsError):
            time.sleep(1.2)
    return {}


def _quote_batch(s: requests.Session, crumb: str, symbols: list[str]) -> list[dict]:
    r = s.get(
        "https://query1.finance.yahoo.com/v7/finance/quote",
        params={"symbols": ",".join(symbols), "crumb": crumb, "fields": QUOTE_FIELDS},
        timeout=20,
    )
    return r.json().get("quoteResponse", {}).get("result", [])


def _add_quotes(got: dict[str, dict], quotes: list[dict]) -> None:
    for quote in quotes:
        if quote.get("quoteType") == "EQUITY" and quote.get("marketCap"):
            got[quote["symbol"]] = quote


def _flipped_symbol(symbol: str) -> str:
    if symbol.endswith(".KS"):
        return symbol.replace(".KS", ".KQ")
    return symbol.replace(".KQ", ".KS")


def _ranked_quotes(syms: dict[str, PoolRow], got: dict[str, dict]) -> list[RankedQuote]:
    rows: list[RankedQuote] = []
    for sym, quote in got.items():
        pool_row = syms[sym]
        price = quote.get("regularMarketPrice")
        high = quote.get("fiftyTwoWeekHigh")
        off = round((price / high - 1) * 100, 1) if price and high else None
        rows.append(
            RankedQuote(
                symbol=sym,
                pool_row=pool_row,
                mcap_eok=quote["marketCap"] / 1e8,
                off_52w_high=off,
            )
        )
    rows.sort(key=lambda row: -row.mcap_eok)
    return rows


def fetch_universe(pool: list[PoolRow], cfg: dict, top_n: int = 100) -> list[Ticker]:
    s, crumb = _session()
    syms = {f"{p['code']}.{p['suffix']}": p for p in pool}
    got = {}
    keys = list(syms)
    for i in range(0, len(keys), 40):
        _add_quotes(got, _quote_batch(s, crumb, keys[i:i + 40]))
        time.sleep(0.4)
    missing = [k for k in keys if k not in got]
    if missing:
        flip = {k: _flipped_symbol(k) for k in missing}
        flipped_to_orig = {flipped: orig for orig, flipped in flip.items()}
        flipped_symbols = list(flipped_to_orig)
        for i in range(0, len(flipped_symbols), 40):
            for quote in _quote_batch(s, crumb, flipped_symbols[i:i + 40]):
                if quote.get("quoteType") == "EQUITY" and quote.get("marketCap"):
                    orig = flipped_to_orig[quote["symbol"]]
                    syms[quote["symbol"]] = syms[orig]
                    got[quote["symbol"]] = quote
            time.sleep(0.4)

    out: list[Ticker] = []
    for quote in _ranked_quotes(syms, got)[:top_n]:
        row = quote.pool_row
        out.append(
            Ticker(
                symbol=row["name"],
                market="KR",
                ccy="KRW",
                sector=row["sector"],
                subsector=row.get("subsector") or None,
                mcap=round(quote.mcap_eok),
                off_52w_high=quote.off_52w_high,
                source="yahoo",
                **_momentum(s, quote.symbol),
            )
        )
        time.sleep(0.25)
    return out
