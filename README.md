# Public Hurdle — Sector Public Hurdle System

> 심사 질문을 "이 회사 좋은가?"에서 **"이 가격이 같은 섹터 최선의 상장 대안 + 프리미엄을 넘는가?"**로 바꾸는 인프라.

비상장 딜의 기대 IRR을 같은 섹터 상장사 워치리스트의 **내재 기대수익률(reverse DCF)**과
동일 선상에서 비교해 PASS / BORDERLINE / FAIL을 판정한다.
운용 전략이 아니라 **심사 규율 도구** — 한 푼도 운용하지 않는다.

```
허들 = mean(top-3 r*, 품질 통과 종목) + 프리미엄(비유동성 5 + 정보열위 3 + 실행리스크 2)
                                        (+ HOT 레짐 자동 가산 2.5%p)
```

산출물은 숫자가 아니라 반증 가능한 문장:

> 본 딜 투자는 [바스켓: A, B, C] 기대수익률 X% + 프리미엄 P%p = 허들 H% 대비 ±Y%p.
> 초과수익의 근거를 IDM '엣지' 섹션에 서면 기재할 것.

## 아키텍처 — 차용한 패턴

| 원본 | 차용 |
|---|---|
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) (69k★) | 프로바이더 추상화 — 소스(Yahoo/FMP/DART)가 표준 모델로 변환된 뒤에만 엔진 진입. "connect once, consume everywhere" |
| [FinanceToolkit](https://github.com/JerBouma/FinanceToolkit) | 투명 계산 — 같은 지표가 소스마다 다른 건 계산법이 숨겨져 있기 때문(MSFT PER 28.9~34.4). 모든 공식을 순수 함수로 노출, 정규화 FCF를 원장에서 직접 계산 |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) (54k★) | 구조화된 설명가능 판정 — 비정형 대화가 아닌 structured report. 판정 카드에 근거 전체가 남는다 |

```
providers/          # 소스별 어댑터 (yahoo 구현 / fmp·dart TODO)
  └→ models.Ticker  # 표준화 — 엔진은 출처를 모른다
engine/
  ├ quality.py      # 버핏식 게이트: ROIC≥15, 마진≥10, 부채≤2x, 성장>0
  ├ dcf.py          # reverse DCF: r*(내재 기대수익률), g*(내재성장률)
  ├ regime.py       # 시총가중 모멘텀 → HOT/NEUTRAL/COLD (리스크 트리거, 매력도 점수 아님)
  └ hurdle.py       # top-3 바스켓 + 프리미엄
deal.py → report.py # YAML 딜 → 판정 카드 (markdown)
config/*.yaml       # 모든 파라미터 외부화 — 프리미엄은 자의적인 게 맞고, 그래서 노출한다
```

## Quickstart

```bash
pip install -e ".[dev]"
pytest -q                                                # 골든 테스트 통과 확인

# 샘플 재무로 허들 산출 (반도체 20종목, 시연용 가짜 재무)
python -m hurdle.cli hurdle --universe data/sample_semis.csv

# 딜 판정
python -m hurdle.cli deal deals/sample_fabless_a.yaml --universe data/sample_semis.csv

# 실데이터: 국내 시총 top-100 (2026-07-03 Yahoo 종가, 재무 미입력 — DART로 채울 것)
python -m hurdle.cli hurdle --universe data/kr_top100.csv

# KR top-100 시세·모멘텀 갱신
python -m hurdle.cli fetch --pool data/kr_pool.csv --out data/kr_top100.csv --top 100

# 로컬 브라우저 UI
python -m hurdle.web
```

## 설계 결정 (요약)

- **정규화 FCF 강제** — TTM으로 돌리면 사이클 피크에서 전 종목이 매수 신호. `FCF₀ = TTM매출 × 3yr 중위마진`, TTM FCF > 1.5×정규화 시 cycle-peak 태그 (V4)
- **top-3 평균** — max는 노이즈, median은 허들 기능 상실. "지금 당장 살 수 있는 최선의 바스켓"이 진짜 기회비용
- **품질 게이트 선행** — 밸류트랩이 허들을 낮추면 시스템 전체 오염
- **레짐 = 트리거** — HOT이면 프리미엄 +2.5%p 자동 가산 + base 배수 −25% 감액 점검 강제. 블로우오프 조항(3M≥40% → 고점比 무관 HOT)은 2026-07 실데이터 캘리브레이션 산물
- **결측 = 탈락** — 조용한 imputation 금지. 재무 미입력 종목은 허들에서 자동 제외
- **유니버스 refresh는 재무 비파괴** — `fetch`는 `mcap`, `ret1m`, `ret3m`, `ret6m`, `off52w`만 새로 쓰고, 기존 `ttmRev > 0` 종목의 `ttmRev`~`cagr` 7개 재무 컬럼은 보존한다.

## 유니버스 자동 갱신 운영

`.github/workflows/refresh-universe.yml`은 평일 16:30 KST에 실행된다. GitHub Actions cron은 UTC 기준이므로 워크플로의 `"30 7 * * 1-5"`가 16:30 KST다.

푸시 후 검증 절차:

1. GitHub 저장소의 Actions 탭에서 `Refresh Universe` 워크플로를 연다.
2. `Run workflow`로 `workflow_dispatch`를 수동 1회 실행한다.
3. 로그에서 `python -m hurdle.cli fetch --pool data/kr_pool.csv --out data/kr_top100.csv --top 100`가 성공했는지 확인한다.
4. 변경이 있을 때만 `data: refresh KR universe` 커밋이 생성되는지 확인한다.

Actions 러너 IP에서 Yahoo crumb 또는 quote가 거부되면 로컬 crontab으로 같은 명령을 실행한다.

```cron
CRON_TZ=Asia/Seoul
30 16 * * 1-5 cd /path/to/public-hurdle && /usr/bin/env bash -lc 'python -m hurdle.cli fetch --pool data/kr_pool.csv --out data/kr_top100.csv --top 100 && git add data/kr_top100.csv && if ! git diff --cached --quiet; then git commit -m "data: refresh KR universe" && git push; fi'
```

## 상태 / 로드맵

v0.1: 엔진 + 레짐 + 판정 + Yahoo 프로바이더 + KR top-100 실데이터(시총·모멘텀). 테스트 통과.
다음: DART/FMP 재무 프로바이더 → top-100 재무 자동 채움 → 웹 UI 포팅.
자세한 작업 순서와 검증 조건(V1~V6)은 `CLAUDE.md`.

## GitHub 푸시

```bash
git init && git add -A && git commit -m "v0.1: engine + regime + verdict + yahoo provider"
gh repo create public-hurdle --private --source . --push
```
