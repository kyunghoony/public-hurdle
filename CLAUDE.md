# public-hurdle — Claude Code 작업 컨텍스트

## 이 시스템이 하는 일
비상장 딜 심사에 "같은 섹터 최선의 상장 대안 + 프리미엄"이라는 허들을 세우는 규율 도구.
운용 전략 아님. 산출물은 반증 가능한 판정 문장.

## 아키텍처 원칙 (위반 금지)
1. 엔진은 데이터 출처를 모른다 — 모든 소스는 models.Ticker로 변환 후 진입 (OpenBB 패턴)
2. 모든 공식은 투명한 순수 함수 — 숨은 계산 금지 (FinanceToolkit 패턴)
3. 판정은 구조화된 설명가능 로그 — 숫자만 뱉지 말 것 (TradingAgents 패턴)
4. 파라미터는 전부 config/*.yaml — 코드 하드코딩 금지
5. 결측 데이터는 0 유지 + 탈락 처리 — 조용한 imputation 절대 금지
6. 레짐은 리스크 트리거로만 작동 — 매력도 점수로 쓰지 말 것

## 검증 조건 (해당 단계 통과 전 다음 단계 진행 금지)
- V1 유니버스: 밴드 필터 후 KR ≥ 5종목. 미달 시 밴드 ±20% 확장 후 로그
- V2 데이터: 필수 필드 완전성 ≥ 80%. 결측 종목 제외 + 로그
- V3 엔진: tests/test_dcf.py 골든 라운드트립(±2bp) + 단조성 통과
- V4 사이클 가드: TTM FCF > 1.5x 정규화 FCF -> cycle-peak 태그 (test_hurdle.py)
- V5 허들: 밸류트랩 제외 + 결정론 (test_hurdle.py)
- V6 E2E: `python -m hurdle.cli deal deals/sample_fabless_a.yaml --universe data/sample_semis.csv` 판정 카드 렌더

## 순서 의존성
providers -> models 변환 -> engine(quality -> dcf) -> regime -> hurdle -> deal -> report
V3 통과 전에 hurdle/deal 작업 금지.

## 다음 작업 (우선순위순)
1. providers/dart.py 구현 — OpenDART 전체재무제표, 계정과목 매핑 테이블 필수. DART_API_KEY 환경변수.
2. providers/fmp.py 구현 — US 재무. FMP_API_KEY.
3. data/kr_top100.csv 재무 컬럼 채우기 (1번 완료 후 자동화)
4. 주간 배치 스크립트 (fetch -> hurdle -> HTML 리포트) + GitHub Actions cron
5. 웹 UI 포팅 (Next.js/Vercel) — 엔진 로직은 이 리포가 single source of truth

## 테스트
pip install -e ".[dev]" && pytest -q  # 전부 통과 상태 유지할 것
