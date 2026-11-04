# HANDOFF — 직전 작업 상태

> 마지막 갱신: 2026-11-04 (Windows)

## 진행 중
- 브랜치 `fix/feedback-learning-loop`에 에이전트별 컨텍스트 관리까지 푸시했다. `main`에는 반영하지 않았고 PR도 없다.
- 주요 파일: `services/memory.py`(`get_agent_contexts`, `build_agent_contexts`), `agents/graph.py`(`rag_node`), `agents/state.py`(`rag_contexts`), 네 에이전트, `tests/test_agent_context.py`.

## 다음에 할 일
- [ ] 실제 OpenAI 키로 전체 흐름과 추천 결과를 확인하고, `RAG_MAX_DISTANCE`를 실제 거리 분포로 조정한다.
- [ ] Docker와 k8s에서 확인한다: 이미지 이름(`localhost:31500`), `alembic upgrade head`, 워커 시작.
- [ ] Supervisor 개선 여부를 정한다 (네 에이전트 유지, 에이전트별 지시 생성과 실패 재시도).
- [ ] PR 생성, pytest를 개발 의존성과 CI에 넣을지 정한다.

## 막힌 점 / 결정 사항
- 세부 분석과 면접 준비 내용은 공개 저장소에 두지 않고 대화와 개인 노트에서 관리한다.
- 컨텍스트: 유사 후보 20건 중 거리 상한 이내에서 에이전트별로 평가된 기록을 최대 5건, 1500자 이내로 고른다. 평가 없는 추천은 넣지 않고, 표시는 최신순이다.
- 프롬프트 개선은 사용자별로 하고, 새 피드백 10개마다 실행한다. 후보 점수가 기본보다 낮으면 기존 프롬프트를 유지한다.
- 테스트는 `backend/`에서 `python -m pytest tests`로 실행한다.
- Windows에서 alembic을 직접 실행하면 `alembic.ini`의 한글 주석 때문에 cp949 오류가 날 수 있다.

## 최근 완료
- 2026-11-03 에이전트별 컨텍스트 관리 구현, 단위 테스트 31개와 전체 흐름 14개 항목 통과 (LLM, 임베딩, Redis는 대체)
- 2026-11-03 DSPy 개선 루프 수정 및 푸시 (`3e72e5d`)
- 2026-11-03 피드백 API 소유자 및 pick_index 검증 추가
