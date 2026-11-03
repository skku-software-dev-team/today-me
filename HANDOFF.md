# HANDOFF — 직전 작업 상태

> 마지막 갱신: 2026-11-03 (Windows)

## 진행 중
- 피드백 API 검증과 사용자별 DSPy 개선 루프 수정을 마쳤고 커밋 전이다.
- 주요 파일: `routers/feedback.py`, `services/memory.py`, `services/dspy_optimizer.py`, `tasks/optimize.py`, `core/celery.py`, `agents/prompt_loader.py`, `models/optimized_prompt.py`, 마이그레이션 `003`, `backend/tests/`, 배포 스크립트, k8s 매니페스트.

## 다음에 할 일
- [ ] 사용자가 내용을 이해한 뒤 별도 브랜치에서 커밋한다.
- [ ] 실제 OpenAI 키로 LLM 검증 단계와 임베딩을 포함해 실행한다.
- [ ] Docker와 k8s에서 확인한다: 이미지 이름(`localhost:31500`), `alembic upgrade head`, 워커 시작.
- [ ] pytest를 개발 의존성과 CI에 넣을지 정한다.

## 막힌 점 / 결정 사항
- 세부 분석 내용은 공개 저장소에 두지 않고 대화와 개인 vault(`20_취업/이력서/`)에서 관리한다.
- 프롬프트 개선은 사용자별로 하고, 새 피드백 10개마다 실행한다. 카운터는 Redis `feedback_count:{user_id}`이며, 코멘트 추가나 평가 변경은 세지 않는다.
- few-shot 예시는 사용자가 실제로 좋아한 최근 추천에서 고르고, 후보 점수가 기본 프롬프트보다 낮으면 기존 프롬프트를 유지한다.
- 테스트는 `backend/`에서 `python -m pytest tests`로 실행한다.
- Windows에서 alembic을 직접 실행하면 `alembic.ini`의 한글 주석 때문에 cp949 오류가 날 수 있다.

## 최근 완료
- 2026-11-03 DSPy 개선 루프 수정, 단위 테스트 22개 통과, 실제 Postgres와 Celery 워커로 전체 흐름 검증 (LLM, 임베딩, Redis는 대체)
- 2026-11-03 피드백 API 소유자 및 pick_index 검증 추가
- 2026-11-03 백엔드, 프론트엔드, k8s, CI 코드 분석
