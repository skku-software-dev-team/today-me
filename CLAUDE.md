# 오늘의 나 (DailyMe) — 프로젝트 컨텍스트

## 프로젝트 한 줄 요약
기분·날씨·에너지·위치를 입력하면 멀티에이전트가 협업해 음악·장소·맛집·스타일을 큐레이션하고, 무드보드 이미지와 "오늘의 무드 리포트"를 생성·기록하는 개인화 PWA.

---

## 핵심 차별점 (이게 이 프로젝트의 전부)
단순 API 오케스트레이션(튜토리얼 티어)에 머물지 않는 두 가지:

1. **취향 메모리 (RAG):** 과거 무드 리포트를 pgvector에 임베딩 저장 → 에이전트 실행 전에 RAG로 컨텍스트 주입. 같은 "비 오는 날"이라도 이 유저의 과거 선택이 반영된 추천이 나와야 함.
2. **학습 루프 (DSPy):** 유저 피드백(좋아요/싫어요) → DSPy로 추천 프롬프트 자기개선 → 취향 메모리 갱신.

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| 에이전트 오케스트레이션 | LangGraph (Supervisor 패턴) |
| 에이전트 간 통신 | MCP (Model Context Protocol) |
| 취향 메모리 | PostgreSQL + pgvector |
| 프롬프트 최적화 | DSPy |
| 백엔드 API | Python (FastAPI 권장), JWT 인증, `/v1/...` 버저닝 |
| 프론트엔드 | React (PWA — 설치/푸시 알림) |
| 외부 API | YouTube Data API (음악), Google Maps/Places (장소·맛집·역지오코딩), OpenWeather (날씨), DALL·E or SD (무드보드 이미지) |
| 인프라 | Docker, Kubernetes, 이미지 잡 큐, Grafana/Prometheus, Jenkins CI/CD |
| 형상관리·이슈 | Jira, GitHub |

> ⚠️ Spotify 사용 불가: 2024년 11월부터 신규 앱에 audio-features·recommendations 엔드포인트 차단. 음악은 YouTube Data API로 검색·링크.

---

## 시스템 아키텍처 (레이어 순서)

```
[React PWA]
  기분 · 날씨 · 에너지 + 위치(동의 기반 자동 수집, 저장은 동/구 단위 일반화)
       ↓  POST /v1/curate
[FastAPI 서버]
       ↓
[오케스트레이터 — LangGraph Supervisor]
  1. pgvector에서 취향 메모리 RAG 조회 → 컨텍스트 구성
  2. 4개 에이전트 병렬 실행
       ├── 음악 에이전트  → YouTube MCP
       ├── 장소 에이전트  → Google Maps MCP
       ├── 맛집 에이전트  → Places/리뷰 MCP
       └── 스타일 에이전트 → (날씨·무드 기반 추론)
  3. DailyState에 결과 병합
  4. 무드보드 이미지 생성 (DALL·E/SD 잡 큐)
       ↓
[PostgreSQL + pgvector]
  - 일별 DailyState 저장
  - 취향 임베딩 저장 (RAG 소스)
  - 피드백 → DSPy 최적화 → 임베딩 갱신
       ↓
[React PWA — 결과 화면]
  - 추천 카드 (음악·장소·맛집·스타일)
  - 무드보드 이미지
  - 히스토리 뷰 (취향 변화 타임라인)
  - 좋아요/싫어요 피드백 UI
```

---

## 공유 상태 스키마 — DailyState

```python
class DailyState(TypedDict):
    # 입력
    user_id: str
    mood: str                  # "지침", "설렘", "차분함" 등
    weather: str               # "맑음", "비", "흐림" 등
    energy: int                # 1~5 (낮음~높음)
    location: Location         # {lat, lng, district}  ← 저장은 district만

    # 에이전트 결과
    music_picks: list[MusicPick]      # [{title, artist, youtube_url}]
    place_picks: list[PlacePick]      # [{name, address, maps_url, reason}]
    food_picks: list[FoodPick]        # [{name, cuisine, address, reason}]
    style_picks: list[StylePick]      # [{description, reason}]
    moodboard_url: str | None

    # 메타
    rag_context: str           # 실행 전 RAG 조회 결과
    llm_calls: list[str]       # 디버깅용 호출 로그
    messages: list[dict]       # 대화 히스토리
    report_id: str | None      # DB 저장 후 채워짐
```

---

## API 계약 — /v1/curate

**Request**
```json
POST /v1/curate
Authorization: Bearer <jwt>

{
  "mood": "지침",
  "weather": "비",
  "energy": 2,
  "location": {
    "lat": 37.5172,
    "lng": 127.0473
  }
}
```

**Response**
```json
{
  "report_id": "uuid",
  "music_picks": [
    { "title": "곡명", "artist": "아티스트", "youtube_url": "https://..." }
  ],
  "place_picks": [
    { "name": "장소명", "address": "주소", "maps_url": "https://...", "reason": "추천 이유" }
  ],
  "food_picks": [
    { "name": "식당명", "cuisine": "한식", "address": "주소", "reason": "추천 이유" }
  ],
  "style_picks": [
    { "description": "코디 설명", "reason": "추천 이유" }
  ],
  "moodboard_url": "https://...",
  "created_at": "2026-06-28T12:00:00Z"
}
```

---

## 에이전트 인터페이스 계약 (모든 에이전트 공통)

```python
class AgentInput(TypedDict):
    state: DailyState          # 공유 상태 전체
    rag_context: str           # 오케스트레이터가 주입한 취향 컨텍스트

class AgentOutput(TypedDict):
    picks: list[dict]          # 에이전트별 결과
    reasoning: str             # 추천 근거 (DSPy 최적화 대상)
    updated_state: DailyState  # 자기 결과 병합 후 상태
```

모든 에이전트는 이 인터페이스를 따름. 오케스트레이터에 등록할 때도 동일 시그니처.

---

## 팀 분담

### 공통 (A·B·C 3명 같이)
- 음악 에이전트 설계 + YouTube API MCP 연동
- 음악 에이전트 = 나머지 4개 에이전트의 **구조적 템플릿**

### A — 오케스트레이션 + API
- LangGraph 흐름 + Supervisor 설계
- 음악 제외 나머지 4개 에이전트 설계 (장소·맛집·스타일·무드보드)
- MCP 도구 연결 (Google Maps, Places, Weather, Claude 비전)
- 프롬프트 설계
- `/v1/curate` API 서버

### B (나) — RAG·학습 + 프론트
- pgvector 취향 메모리 (임베딩 저장·조회·인덱싱)
- 실행 전 RAG 주입 (오케스트레이터 호출 전 컨텍스트 구성)
- DSPy 최적화 (피드백 → 프롬프트 자기개선 루프)
- React PWA (결과 카드·히스토리 뷰·피드백 UI·설치/푸시)

### C — 인프라/플랫폼
- K8s + 이미지 잡 큐 (무드보드 생성 비동기 처리)
- Grafana/Prometheus (에이전트 지연·LLM 비용·추천 품질 메트릭)
- Jenkins CI/CD
- Postgres 운영 (마이그레이션·백업·인덱스)

---

## 개발 순서 (4단계)

| 단계 | 주차 | 목표 |
|---|---|---|
| 기반·템플릿 | W1–2 | 다 같이 음악 에이전트로 골든패스 완성 + API 계약 확정 |
| 에이전트 분산 | W3–4 | 각자 트랙 병행하며 나머지 에이전트 → **W4 = MVP ★** |
| 심화 | W5–6 | RAG·DSPy 부착, 피드백 학습 루프 완성 |
| 운영·마무리 | W7–8 | 배포·관측·데모·문서 |

**사수해야 할 마일스톤:**
- W2 끝: 음악 에이전트가 화면까지 실제로 돈다
- W4 끝 ★: 5개 에이전트 + 무드보드 + 히스토리 MVP 데모 가능
- W6 끝: DSPy 학습 루프 동작 (포트폴리오 전환점)
- W8 끝: 배포·관측·문서 완비

---

## 협업 규칙
1. **W1에 에이전트 인터페이스 계약 + DailyState + /v1/curate 못 박기** — 수직 분담의 생명줄. 셋이 병렬로 일하려면 이게 먼저.
2. **W2 이후 end-to-end 절대 안 깨기** — 새 기능은 항상 "돌아가는 상태"에서 얹기.
3. 2주 스프린트 + 주간 코드리뷰, Jira 운영.

---

## B 트랙이 특히 신경 쓸 것

**pgvector 취향 메모리 설계 포인트:**
- 임베딩 대상: 과거 DailyState (mood + weather + energy + picks + feedback)
- 조회 시점: 오케스트레이터가 에이전트 호출 *전에* 코사인 유사도 검색으로 top-k 컨텍스트 구성
- 저장 시점: 리포트 생성 후 + 피드백 수신 후 갱신
- 인덱스: ivfflat or hnsw (C가 Postgres 운영이지만, 인덱스 스펙은 B가 정의)

**DSPy 최적화 포인트:**
- 최적화 대상: 각 에이전트의 추천 프롬프트 (reasoning 필드)
- 학습 신호: 좋아요(+1) / 싫어요(-1) 피드백
- 평가 메트릭: 피드백 점수 누적 평균 (C가 Grafana로 시각화)

**React PWA 포인트:**
- 위치 동의 UX: 첫 진입 시 Geolocation 권한 요청, 거부 시 도시명 직접 입력 폴백
- 히스토리 뷰: 날짜별 DailyState 타임라인, 취향 변화 시각화
- 피드백 UI: 각 pick 카드에 좋아요/싫어요, 전송은 `POST /v1/feedback`
- PWA: manifest.json + service worker, 푸시 알림("오늘의 무드 리포트 준비됨")
- API 호출: 목(mock) 서버로 먼저 UI 잡고, W2에 실 API로 교체
