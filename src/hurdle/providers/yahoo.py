"""Yahoo Finance 프로바이더 — cookie+crumb 배치 쿼트 + v8 차트 모멘텀.

2026-07-03 검증 완료 경로. KRX 로그인화(pykrx 사망)·네이버 차단 환경에서의 차선.
한계: 시총의 주식수 반영 시차 가능 -> 사용 전 KRX/네이버 크로스체크 권장.
"""
import time
import requests
from ..models import Ticker

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36"}


def _session() -> tuple[requests.Session, str]:
    s = requests.Session()
    s.headers.update(UA)
    s.get("https://fc.yahoo.com", timeout=10)
    crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10).text.strip()
    return s, crumb


def _momentum(s: requests.Session, sym: str) -> dict:
    for _ in range(2):
        try:
            r = s.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                      params={"range": "1y", "interval": "1d"}, timeout=15)
            if r.status_code == 429:
                time.sleep(2.5)
                continue
            closes = [c for c in r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
            if len(closes) < 130:
                return {}
            last = closes[-1]
            ret = lambda n: round((last / closes[-1 - n] - 1) * 100, 1)
            return {"ret_1m": ret(21), "ret_3m": ret(63), "ret_6m": ret(126)}
        except Exception:
            time.sleep(1.2)
    return {}


def fetch_universe(pool: list[dict], cfg: dict, top_n: int = 100) -> list[Ticker]:
    """pool: [{code, suffix, name, sector, subsector}] -> 시총 랭킹 top_n + 모멘텀."""
    s, crumb = _session()
    syms = {f"{p['code']}.{p['suffix']}": p for p in pool}
    got = {}
    keys = list(syms)
    for i in range(0, len(keys), 40):
        r = s.get("https://query1.finance.yahoo.com/v7/finance/quote",
                  params={"symbols": ",".join(keys[i:i + 40]), "crumb": crumb,
                          "fields": "shortName,marketCap,fiftyTwoWeekHigh,regularMarketPrice,quoteType"},
                  timeout=20)
        for it in r.json().get("quoteResponse", {}).get("result", []):
            if it.get("quoteType") == "EQUITY" and it.get("marketCap"):
                got[it["symbol"]] = it
        time.sleep(0.4)
    # 미수신 -> 거래소 접미사 flip 재시도
    missing = [k for k in keys if k not in got]
    if missing:
        flip = {k: k.replace(".KS", ".KQ") if k.endswith(".KS") else k.replace(".KQ", ".KS") for k in missing}
        r = s.get("https://query1.finance.yahoo.com/v7/finance/quote",
                  params={"symbols": ",".join(flip.values()), "crumb": crumb,
                          "fields": "shortName,marketCap,fiftyTwoWeekHigh,regularMarketPrice,quoteType"},
                  timeout=20)
        for it in r.json().get("quoteResponse", {}).get("result", []):
            if it.get("quoteType") == "EQUITY" and it.get("marketCap"):
                orig = next(k for k, v in flip.items() if v == it["symbol"])
                syms[it["symbol"]] = syms[orig]
                got[it["symbol"]] = it

    rows = []
    for sym, it in got.items():
        p = syms[sym]
        price, hi = it.get("regularMarketPrice"), it.get("fiftyTwoWeekHigh")
        rows.append((sym, p, it["marketCap"] / 1e8,
                     round((price / hi - 1) * 100, 1) if price and hi else None))
    rows.sort(key=lambda x: -x[2])
    out = []
    for sym, p, mcap_eok, off in rows[:top_n]:
        mom = _momentum(s, sym)
        out.append(Ticker(symbol=p["name"], market="KR", ccy="KRW",
                          sector=p["sector"], subsector=p.get("subsector"),
                          mcap=round(mcap_eok), off_52w_high=off, source="yahoo", **mom))
        time.sleep(0.25)
    return out
