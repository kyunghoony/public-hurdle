from hurdle.models import Ticker
from hurdle.refresh import merge_financials, merge_universe


def _ticker(name: str, *, mcap: float = 0.0, ttm_rev: float = 0.0) -> Ticker:
    return Ticker(
        symbol=name,
        market="KR",
        ccy="KRW",
        sector="old-sector",
        subsector="old-sub",
        mcap=mcap,
        ttm_rev=ttm_rev,
        ttm_fcf=11.0,
        fcf_margin_3y=12.0,
        growth=13.0,
        roic_3y=14.0,
        netdebt_ebitda=1.5,
        rev_cagr_3y=16.0,
    )


def test_merge_universe_preserves_financials_and_updates_market_data():
    # Given: an old row with financials and fresh market data for the same ticker.
    old = [_ticker("기존", mcap=100.0, ttm_rev=10.0)]
    fresh = [
        Ticker(
            symbol="기존",
            market="KR",
            ccy="KRW",
            sector="new-sector",
            subsector=None,
            mcap=200.0,
            ret_1m=1.1,
            ret_3m=3.3,
            ret_6m=6.6,
            off_52w_high=-9.9,
        )
    ]

    # When: the universe rows are merged.
    [row] = merge_universe(fresh, old)

    # Then: fresh market fields win, while old financial fields remain intact.
    assert row["mcap"] == "200"
    assert row["ret1m"] == "1.1"
    assert row["ret3m"] == "3.3"
    assert row["ret6m"] == "6.6"
    assert row["off52w"] == "-9.9"
    assert row["sector"] == "old-sector"
    assert row["subsector"] == "old-sub"
    assert row["ttmRev"] == "10"
    assert row["ttmFCF"] == "11"
    assert row["margin3y"] == "12"
    assert row["growth"] == "13"
    assert row["roic"] == "14"
    assert row["ndEbitda"] == "1.5"
    assert row["cagr"] == "16"


def test_merge_universe_blanks_financials_for_new_entries():
    # Given: fresh market data for a ticker absent from the old universe.
    fresh = [Ticker(symbol="신규", market="KR", ccy="KRW", sector="new-sector", mcap=300.0)]

    # When: the new ticker is merged into CSV rows.
    [row] = merge_universe(fresh, [])

    # Then: no financial values are imputed.
    assert row["ticker"] == "신규"
    assert row["mcap"] == "300"
    assert row["ttmRev"] == ""
    assert row["ttmFCF"] == ""
    assert row["margin3y"] == ""
    assert row["growth"] == ""
    assert row["roic"] == ""
    assert row["ndEbitda"] == ""
    assert row["cagr"] == ""


def test_merge_universe_blanks_old_zero_financials():
    # Given: an old ticker with no populated revenue.
    old = [_ticker("무재무", mcap=100.0, ttm_rev=0.0)]
    fresh = [Ticker(symbol="무재무", market="KR", ccy="KRW", sector="fresh-sector", mcap=250.0)]

    # When: the ticker is refreshed.
    [row] = merge_universe(fresh, old)

    # Then: zero financials are not written back as filled data.
    assert row["mcap"] == "250"
    assert row["ttmRev"] == ""
    assert row["ttmFCF"] == ""
    assert row["margin3y"] == ""
    assert row["growth"] == ""
    assert row["roic"] == ""
    assert row["ndEbitda"] == ""
    assert row["cagr"] == ""


def test_merge_financials_updates_only_financial_columns():
    # Given: an old market row and a DART-filled ticker for the same company.
    old = [
        Ticker(
            symbol="기존",
            market="KR",
            ccy="KRW",
            sector="old-sector",
            subsector="old-sub",
            mcap=123.0,
            ret_1m=1.0,
            ret_3m=3.0,
            ret_6m=6.0,
            off_52w_high=-7.0,
        )
    ]
    filled = [_ticker("기존", mcap=999.0, ttm_rev=10.0)]

    # When: financials are merged into the existing universe.
    [row] = merge_financials(filled, old)

    # Then: market and momentum stay untouched while DART financials are written.
    assert row["mcap"] == "123"
    assert row["ret1m"] == "1"
    assert row["ret3m"] == "3"
    assert row["ret6m"] == "6"
    assert row["off52w"] == "-7"
    assert row["ttmRev"] == "10"
    assert row["ttmFCF"] == "11"
    assert row["margin3y"] == "12"
    assert row["growth"] == "13"
    assert row["roic"] == "14"
    assert row["ndEbitda"] == "1.5"
    assert row["cagr"] == "16"


def test_merge_financials_preserves_old_financials_when_dart_missing():
    # Given: an old row with financials and a DART result that failed to populate them.
    old = [_ticker("기존", mcap=100.0, ttm_rev=10.0)]
    filled = [Ticker(symbol="기존", market="KR", ccy="KRW", sector="old-sector", mcap=100.0)]

    # When: missing DART output is merged.
    [row] = merge_financials(filled, old)

    # Then: the previous financials are not erased.
    assert row["ttmRev"] == "10"
    assert row["ttmFCF"] == "11"


def test_merge_financials_blanks_when_no_financial_source_exists():
    # Given: neither the old CSV nor DART has usable revenue.
    old = [_ticker("무재무", mcap=100.0, ttm_rev=0.0)]
    filled = [Ticker(symbol="무재무", market="KR", ccy="KRW", sector="old-sector", mcap=100.0)]

    # When: financials are merged.
    [row] = merge_financials(filled, old)

    # Then: no financial values are imputed.
    assert row["ttmRev"] == ""
    assert row["ttmFCF"] == ""
    assert row["margin3y"] == ""
    assert row["growth"] == ""
    assert row["roic"] == ""
    assert row["ndEbitda"] == ""
    assert row["cagr"] == ""
