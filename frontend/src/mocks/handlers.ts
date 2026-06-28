import { http, HttpResponse, delay } from "msw";

// ─── 목 데이터 생성 ───────────────────────────────────────────────

function makeMusicPicks(energy: number) {
  const low = [
    { title: "밤편지", artist: "IU", youtube_url: "https://www.youtube.com/watch?v=BzYnNdJhZQw" },
    { title: "비도 오고 그래서", artist: "헤이즈", youtube_url: "https://www.youtube.com/watch?v=2KKDPBIFRMk" },
    { title: "사랑이 잘", artist: "IU ft. 오혁", youtube_url: "https://www.youtube.com/watch?v=P21HJsHr_mU" },
  ];
  const high = [
    { title: "Dynamite", artist: "BTS", youtube_url: "https://www.youtube.com/watch?v=gdZLi9oWNZg" },
    { title: "Next Level", artist: "aespa", youtube_url: "https://www.youtube.com/watch?v=4TWR90KJl84" },
    { title: "ANTIFRAGILE", artist: "LE SSERAFIM", youtube_url: "https://www.youtube.com/watch?v=Yk4H9i4vGg4" },
  ];
  return energy <= 2 ? low : high;
}

function makePlacePicks(mood: string) {
  const calm = [
    { name: "북서울꿈의숲", address: "서울 강북구 월계로 173", maps_url: "https://maps.google.com/?q=북서울꿈의숲", reason: `"${mood}" 기분에 산책로와 넓은 잔디밭이 마음을 차분하게 해줍니다.` },
    { name: "국립중앙도서관", address: "서울 서초구 반포대로 201", maps_url: "https://maps.google.com/?q=국립중앙도서관", reason: "조용한 공간에서 생각을 정리하기 좋습니다." },
  ];
  const active = [
    { name: "한강공원 뚝섬지구", address: "서울 광진구 강변북로 139", maps_url: "https://maps.google.com/?q=뚝섬한강공원", reason: `"${mood}" 에너지를 발산하기 좋은 탁 트인 공간입니다.` },
    { name: "남산타워", address: "서울 용산구 남산공원길 105", maps_url: "https://maps.google.com/?q=남산타워", reason: "서울 전경을 바라보며 기분 전환에 딱입니다." },
  ];
  const keywords = ["지침", "우울", "차분", "피곤"];
  const isCalm = keywords.some((k) => mood.includes(k));
  return isCalm ? calm : active;
}

function makeFoodPicks(energy: number) {
  const light = [
    { name: "오봉집", cuisine: "한식", address: "서울 마포구 와우산로 29", reason: "부드러운 국밥으로 몸과 마음을 달래줍니다." },
    { name: "스타벅스 합정점", cuisine: "카페", address: "서울 마포구 양화로 45", reason: "조용한 카페에서 가볍게 쉬기 좋습니다." },
  ];
  const hearty = [
    { name: "마포갈매기", cuisine: "고기", address: "서울 마포구 토정로 35", reason: "에너지 충전에 고기만한 게 없죠." },
    { name: "진주회관", cuisine: "한식", address: "서울 서대문구 충정로 60", reason: "콩국수로 든든하게 채워보세요." },
  ];
  return energy <= 2 ? light : hearty;
}

function makeStylePicks(mood: string, energy: number) {
  if (energy <= 2) {
    return [
      { description: "오버사이즈 후드티 + 조거 팬츠 + 슬리퍼", reason: "편안함이 최우선인 날. 컬러는 베이지·그레이 톤으로." },
      { description: "루즈핏 린넨 셔츠 + 와이드 팬츠", reason: `"${mood}" 기분엔 몸을 조이지 않는 넉넉한 실루엣이 제격입니다.` },
    ];
  }
  return [
    { description: "크롭 재킷 + 하이웨이스트 진 + 스니커즈", reason: "활동적인 하루에 잘 어울리는 스트릿 룩." },
    { description: "컬러풀 니트 + 미니스커트 + 청키 부츠", reason: `"${mood}" 기분을 옷으로도 표현해보세요.` },
  ];
}

const MOCK_REPORT_ID = "550e8400-e29b-41d4-a716-446655440000";

// ─── 핸들러 ──────────────────────────────────────────────────────

export const handlers = [
  // POST /v1/curate
  http.post("/v1/curate", async ({ request }) => {
    await delay(1500);
    const body = await request.json() as { mood: string; energy: number; location: { lat: number; lng: number } };
    const { mood = "평범함", energy = 3 } = body;

    return HttpResponse.json({
      report_id: MOCK_REPORT_ID,
      music_picks: makeMusicPicks(energy),
      place_picks: makePlacePicks(mood),
      food_picks: makeFoodPicks(energy),
      style_picks: makeStylePicks(mood, energy),
      moodboard_url: "https://picsum.photos/seed/dailyme/800/600",
      created_at: new Date().toISOString(),
    });
  }),

  // POST /v1/feedback
  http.post("/v1/feedback", async () => {
    await delay(200);
    return HttpResponse.json({ status: "ok" });
  }),

  // GET /v1/history
  http.get("/v1/history", async ({ request }) => {
    await delay(600);
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get("limit") ?? 20);
    const offset = Number(url.searchParams.get("offset") ?? 0);

    const all = [
      { report_id: MOCK_REPORT_ID, mood: "지침", weather: "비", energy: 2, moodboard_url: "https://picsum.photos/seed/r1/400/300", created_at: "2026-06-28T12:00:00Z" },
      { report_id: "a1b2c3d4-0000-0000-0000-000000000001", mood: "설렘", weather: "맑음", energy: 4, moodboard_url: "https://picsum.photos/seed/r2/400/300", created_at: "2026-06-27T09:00:00Z" },
      { report_id: "a1b2c3d4-0000-0000-0000-000000000002", mood: "오늘 뭔가 새로운 걸 해보고 싶은 날", weather: "흐림", energy: 3, moodboard_url: "https://picsum.photos/seed/r3/400/300", created_at: "2026-06-26T18:30:00Z" },
      { report_id: "a1b2c3d4-0000-0000-0000-000000000003", mood: "차분함", weather: "맑음", energy: 2, moodboard_url: "https://picsum.photos/seed/r4/400/300", created_at: "2026-06-25T08:00:00Z" },
    ];

    const sliced = all.slice(offset, offset + limit);
    return HttpResponse.json({ total: all.length, reports: sliced });
  }),

  // auth mock — 백엔드 없이도 로그인 상태 유지
  http.post("/api/auth/refresh", async () => {
    await delay(100);
    return HttpResponse.json({ access_token: "mock-jwt-token-for-dev" });
  }),

  http.post("/api/auth/logout", async () => {
    await delay(100);
    return HttpResponse.json({ status: "ok" });
  }),
];
