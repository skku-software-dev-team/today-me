"""무드보드 에이전트 — 4개 에이전트 결과를 종합해 HuggingFace로 하루를 한 장의 이미지로 생성."""

import base64
import logging
import os
from io import BytesIO

from huggingface_hub import AsyncInferenceClient

from app.agents.state import DailyState

logger = logging.getLogger("moodboard_agent")

_HF_MODEL = "black-forest-labs/FLUX.1-schnell"

_ENERGY_WORDS = {
    1: "completely drained and still",
    2: "low and quiet",
    3: "calm and balanced",
    4: "lively and light",
    5: "vibrant and full of life",
}

# 무드 키워드 → 색상 팔레트 설명
_MOOD_PALETTE: list[tuple[list[str], str]] = [
    (["우울", "슬픔", "슬프", "우울함", "depressed", "sad"],
     "muted blue-gray and desaturated cool tones, dim and overcast palette"),
    (["지침", "피곤", "무기력", "지쳐", "tired", "exhausted"],
     "dusty gray and muted earth tones, low-saturation washed-out palette"),
    (["불안", "걱정", "긴장", "anxious", "nervous"],
     "cool gray and deep muted teal, unsettled desaturated palette"),
    (["화남", "짜증", "분노", "angry", "frustrated"],
     "deep charcoal and muted burgundy, dark moody tones"),
    (["설렘", "기대", "두근", "excited", "thrilled"],
     "warm peach, soft coral and golden yellow, bright uplifting palette"),
    (["행복", "기쁨", "즐거", "happy", "joyful"],
     "warm ivory, soft peach and sky blue, cheerful light palette"),
    (["차분", "평온", "편안", "calm", "peaceful", "relaxed"],
     "sage green, dusty rose and warm beige, soft muted palette"),
    (["활기", "에너지", "신남", "energetic", "lively"],
     "vivid terracotta, bright mustard and cobalt, bold saturated palette"),
]

_DEFAULT_PALETTE = "soft neutral tones with warm beige and cream"


def _mood_to_palette(mood: str) -> str:
    mood_lower = mood.lower()
    for keywords, palette in _MOOD_PALETTE:
        if any(kw in mood_lower for kw in keywords):
            return palette
    return _DEFAULT_PALETTE

# 한국어 패션 용어 → 영어 (긴 표현 먼저 매칭되도록 내림차순 정렬해서 사용)
_KO_EN: dict[str, str] = {
    # 색상
    "딥 그레이": "deep gray", "연청": "light blue denim", "흑청": "dark denim",
    "파스텔 베이지": "pastel beige", "파스텔": "pastel", "베이지": "beige",
    "화이트": "white", "블랙": "black", "그레이": "gray", "네이비": "navy",
    "카키": "khaki", "아이보리": "ivory", "브라운": "brown", "크림": "cream",
    "올리브": "olive", "버건디": "burgundy", "머스타드": "mustard",
    "민트": "mint", "라벤더": "lavender", "코랄": "coral", "와인": "wine red",
    # 핏/스타일
    "오버사이즈": "oversized", "오버핏": "oversized", "슬림핏": "slim fit",
    # 아이템
    "더블 코트": "double-breasted coat", "트렌치코트": "trench coat",
    "후드티": "hoodie", "가디건": "cardigan", "블레이저": "blazer",
    "니트": "knit sweater", "코트": "coat", "재킷": "jacket",
    "셔츠": "shirt", "티셔츠": "t-shirt", "원피스": "dress",
    "조거 팬츠": "jogger pants", "팬츠": "trousers", "스커트": "skirt",
    "청바지": "jeans", "레깅스": "leggings",
    "스니커즈": "sneakers", "로퍼": "loafers", "부츠": "boots",
    "슬리퍼": "slippers", "하이힐": "heels", "플랫슈즈": "flat shoes",
    "크로스백": "crossbody bag", "토트백": "tote bag", "백팩": "backpack",
    "가방": "bag",
}


def _translate_style(text: str) -> str:
    for ko, en in sorted(_KO_EN.items(), key=lambda x: -len(x[0])):
        text = text.replace(ko, en)
    return text


def build_image_prompt(
    mood: str,
    weather: str,
    energy: int,
    music_picks: list | None = None,
    place_picks: list | None = None,
    food_picks: list | None = None,
    style_picks: list | None = None,
) -> str:
    music_picks = music_picks or []
    place_picks = place_picks or []
    food_picks = food_picks or []
    style_picks = style_picks or []

    energy_word = _ENERGY_WORDS.get(energy, "calm and balanced")

    place_desc = (
        ", ".join(p["name"] for p in place_picks[:2])
        if place_picks else ""
    )
    food_desc = (
        ", ".join(f'{f["name"]} ({f["cuisine"]})' for f in food_picks[:2])
        if food_picks else ""
    )
    # 스타일 첫 번째 추천만, 한국어 → 영어 변환
    style_desc = _translate_style(style_picks[0]["description"]) if style_picks else ""

    palette = _mood_to_palette(mood)

    parts = [
        f"Today's mood is '{mood}', weather is {weather}, energy feels {energy_word}.",
    ]
    if place_desc:
        parts.append(f"The scene evokes places like {place_desc}.")
    if food_desc:
        parts.append(f"Subtle food imagery: {food_desc}.")
    if style_desc:
        parts.append(f"Featured outfit: {style_desc}.")
    parts.append(
        f"Color palette: {palette}. "
        "Art style: photorealistic Pinterest fashion mood board collage, "
        "multiple real photograph panels arranged on a soft background, "
        "actual product photos and lifestyle photography (not illustrations, not drawings, not flat art), "
        "color swatches matching the mood palette, Korean fashion editorial aesthetic, "
        "outfit flat-lay photography, real food photos, real place photography as collage tiles, "
        "soft natural lighting, layered paper textures. "
        "No text, no faces, no illustrations, no cartoons, photography only."
    )

    return " ".join(parts)


async def moodboard_agent_node(state: DailyState) -> dict:
    prompt = build_image_prompt(
        mood=state["mood"],
        weather=state.get("weather", ""),
        energy=state.get("energy", 3),
        music_picks=state.get("music_picks", []),
        place_picks=state.get("place_picks", []),
        food_picks=state.get("food_picks", []),
        style_picks=state.get("style_picks", []),
    )
    logger.info("moodboard prompt: %s", prompt[:400])

    try:
        client = AsyncInferenceClient(
            model=_HF_MODEL,
            token=os.environ.get("HF_API_TOKEN"),
        )
        image = await client.text_to_image(prompt=prompt, width=1024, height=576)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        url = f"data:image/png;base64,{b64}"
        logger.info("moodboard 생성 완료 (b64 len=%d)", len(b64))
        return {"moodboard_url": url}
    except Exception as exc:
        logger.error("moodboard 생성 실패: %s", exc)
        return {"moodboard_url": None}
