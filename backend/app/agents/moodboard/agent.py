"""무드보드 에이전트 — 4개 에이전트 결과를 종합해 gpt-image-1로 하루를 한 장의 이미지로 생성."""

import logging
import os

from openai import AsyncOpenAI

from app.agents.state import DailyState

logger = logging.getLogger("moodboard_agent")

_ENERGY_WORDS = {
    1: "completely drained and still",
    2: "low and quiet",
    3: "calm and balanced",
    4: "lively and light",
    5: "vibrant and full of life",
}


def build_gpt_image_prompt(
    mood: str,
    weather: str,
    energy: int,
    music_picks: list = [],
    place_picks: list = [],
    food_picks: list = [],
    style_picks: list = [],
) -> str:
    energy_word = _ENERGY_WORDS.get(energy, "calm and balanced")

    music_desc = (
        ", ".join(f'"{m["title"]}" by {m["artist"]}' for m in music_picks[:2])
        if music_picks else ""
    )
    place_desc = (
        ", ".join(p["name"] for p in place_picks[:2])
        if place_picks else ""
    )
    food_desc = (
        ", ".join(f'{f["name"]} ({f["cuisine"]})' for f in food_picks[:2])
        if food_picks else ""
    )
    style_desc = style_picks[0]["description"] if style_picks else ""

    parts = [
        f"A single cinematic lifestyle illustration capturing today's mood: '{mood}'.",
        f"The weather is {weather}, the overall energy feels {energy_word}.",
    ]
    if place_desc:
        parts.append(f"The scene evokes places like {place_desc}.")
    if food_desc:
        parts.append(f"Subtle food imagery: {food_desc}.")
    if style_desc:
        parts.append(f"The fashion in the scene: {style_desc}.")
    if music_desc:
        parts.append(f"The visual rhythm is inspired by {music_desc}.")
    parts.append(
        "Art style: Pinterest-style fashion mood board collage layout, "
        "multiple aesthetic photo panels and cards arranged on a soft textured cream background, "
        "pastel color palette swatches in the corner, Korean fashion editorial magazine aesthetic, "
        "outfit flat-lays, lifestyle objects, food and place imagery as collage tiles, "
        "ring-bound journal detail, dreamy airy tones, layered paper textures. "
        "No readable text, no faces."
    )

    return " ".join(parts)


async def moodboard_agent_node(state: DailyState) -> dict:
    prompt = build_gpt_image_prompt(
        mood=state["mood"],
        weather=state.get("weather", ""),
        energy=state.get("energy", 3),
        music_picks=state.get("music_picks", []),
        place_picks=state.get("place_picks", []),
        food_picks=state.get("food_picks", []),
        style_picks=state.get("style_picks", []),
    )
    logger.info("moodboard prompt: %s", prompt[:300])

    try:
        client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = await client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1536x1024",
            n=1,
        )
        item = response.data[0]
        # gpt-image-1 은 b64_json 반환, dall-e-3 은 url 반환 — 둘 다 대응
        if getattr(item, "url", None):
            url = item.url
        else:
            url = f"data:image/png;base64,{item.b64_json}"
        logger.info("moodboard 생성 완료 (len=%d)", len(url))
        return {"moodboard_url": url}
    except Exception as exc:
        logger.error("moodboard 생성 실패: %s", exc)
        return {"moodboard_url": None}
