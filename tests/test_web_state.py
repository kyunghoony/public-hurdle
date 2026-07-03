import csv
from pathlib import Path

from hurdle.models import Ticker
from hurdle.web_state import WebPaths, build_state, fill_financials_state, refresh_state


HEADER = [
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
]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _write_pool(path: Path) -> None:
    path.write_text(
        "code,suffix,name,sector,subsector\n005930,KS,삼성전자,반도체,chip\n",
        encoding="utf-8",
    )


def test_build_state_summarizes_universe_for_browser(tmp_path):
    # Given: a small universe with one financially populated ticker.
    universe = tmp_path / "universe.csv"
    pool = tmp_path / "pool.csv"
    _write_pool(pool)
    _write_csv(
        universe,
        [
            {
                "ticker": "삼성전자",
                "market": "KR",
                "ccy": "KRW",
                "sector": "반도체",
                "subsector": "chip",
                "mcap": "1000",
                "ttmRev": "100",
                "ttmFCF": "20",
                "margin3y": "20",
                "growth": "10",
                "roic": "20",
                "ndEbitda": "1",
                "cagr": "5",
                "ret1m": "1",
                "ret3m": "2",
                "ret6m": "3",
                "off52w": "-4",
            }
        ],
    )
    paths = WebPaths(universe=universe, pool=pool, config=Path("config/semiconductor.yaml"))

    # When: the browser state payload is built.
    state = build_state(paths)

    # Then: summary and row fields are ready for JSON rendering.
    assert state["summary"]["count"] == 1
    assert state["summary"]["financialCount"] == 1
    assert state["summary"]["totalMcap"] == 1000
    assert state["rows"][0]["ticker"] == "삼성전자"
    assert state["rows"][0]["qualityPass"] is True


def test_refresh_state_preserves_existing_financials_with_fake_fetcher(tmp_path):
    # Given: an existing output CSV and a fake provider returning fresh market data.
    universe = tmp_path / "universe.csv"
    pool = tmp_path / "pool.csv"
    _write_pool(pool)
    _write_csv(
        universe,
        [
            {
                "ticker": "삼성전자",
                "market": "KR",
                "ccy": "KRW",
                "sector": "반도체",
                "subsector": "chip",
                "mcap": "1000",
                "ttmRev": "100",
                "ttmFCF": "20",
                "margin3y": "20",
                "growth": "10",
                "roic": "20",
                "ndEbitda": "1",
                "cagr": "5",
                "ret1m": "1",
                "ret3m": "2",
                "ret6m": "3",
                "off52w": "-4",
            }
        ],
    )
    paths = WebPaths(universe=universe, pool=pool, config=Path("config/semiconductor.yaml"))

    def fake_fetcher(_pool, _cfg, _top_n):
        return [
            Ticker(
                symbol="삼성전자",
                market="KR",
                ccy="KRW",
                sector="새분류",
                mcap=2000,
                ret_1m=11,
                ret_3m=22,
                ret_6m=33,
                off_52w_high=-8,
            )
        ]

    # When: refresh runs through the same merge path as the UI button.
    state = refresh_state(paths, top_n=1, fetcher=fake_fetcher)

    # Then: market data updates while existing financials remain populated.
    row = state["rows"][0]
    assert state["refresh"]["preservedCount"] == 1
    assert row["mcap"] == 2000
    assert row["ret3m"] == 22
    assert row["ttmRev"] == 100
    assert row["sector"] == "반도체"


def test_fill_financials_state_writes_dart_financials_without_market_changes(tmp_path):
    # Given: an existing universe with market data but no financials.
    universe = tmp_path / "universe.csv"
    pool = tmp_path / "pool.csv"
    _write_pool(pool)
    _write_csv(
        universe,
        [
            {
                "ticker": "삼성전자",
                "market": "KR",
                "ccy": "KRW",
                "sector": "반도체",
                "subsector": "chip",
                "mcap": "1000",
                "ttmRev": "",
                "ttmFCF": "",
                "margin3y": "",
                "growth": "",
                "roic": "",
                "ndEbitda": "",
                "cagr": "",
                "ret1m": "1",
                "ret3m": "2",
                "ret6m": "3",
                "off52w": "-4",
            }
        ],
    )
    paths = WebPaths(universe=universe, pool=pool, config=Path("config/semiconductor.yaml"))

    def fake_filler(tickers):
        [ticker] = tickers
        return [
            Ticker(
                symbol=ticker.symbol,
                market=ticker.market,
                ccy=ticker.ccy,
                sector=ticker.sector,
                subsector=ticker.subsector,
                mcap=9999,
                ttm_rev=100,
                ttm_fcf=20,
                fcf_margin_3y=20,
                growth=10,
                roic_3y=20,
                netdebt_ebitda=1,
                rev_cagr_3y=5,
            )
        ]

    # When: financial fill runs through the browser state path.
    state = fill_financials_state(paths, filler=fake_filler)

    # Then: financials are written while existing market fields remain unchanged.
    row = state["rows"][0]
    assert state["financials"]["filledCount"] == 1
    assert state["financials"]["oldFinancialCount"] == 0
    assert state["financials"]["missing"] == []
    assert row["mcap"] == 1000
    assert row["ret3m"] == 2
    assert row["ttmRev"] == 100
    assert row["ttmFCF"] == 20
