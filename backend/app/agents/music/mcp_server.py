"""YouTube Data API를 MCP 도구로 노출하는 FastMCP 서버.

에이전트가 stdio transport로 이 프로세스를 스폰해서 사용한다.
실행: python -m app.agents.music.mcp_server
"""

import os
import re

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("youtube-music")

_YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _api_key() -> str:
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY 환경변수가 없습니다.")
    return key


@mcp.tool()
async def search_music(query: str, max_results: int = 5) -> list[dict]:
    """YouTube에서 음악을 검색한다.

    Args:
        query: 검색어 (예: "비 오는 날 감성 재즈")
        max_results: 최대 결과 수 (1~10)
    """
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "10",  # Music
        "maxResults": max_results,
        "key": _api_key(),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_YOUTUBE_API_BASE}/search", params=params)
        resp.raise_for_status()

    results = []
    for item in resp.json().get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        results.append(
            {
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "video_id": video_id,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )
    return results


@mcp.tool()
async def get_video_details(video_id: str) -> dict:
    """YouTube 영상의 상세 정보(길이, 조회수)를 가져온다.

    Args:
        video_id: YouTube 영상 ID
    """
    params = {
        "part": "snippet,contentDetails,statistics",
        "id": video_id,
        "key": _api_key(),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_YOUTUBE_API_BASE}/videos", params=params)
        resp.raise_for_status()

    items = resp.json().get("items", [])
    if not items:
        return {}

    item = items[0]
    duration_str = item["contentDetails"]["duration"]
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    h, m, s = (int(match.group(i) or 0) for i in (1, 2, 3)) if match else (0, 0, 0)

    return {
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "duration_seconds": h * 3600 + m * 60 + s,
        "view_count": int(item.get("statistics", {}).get("viewCount", 0)),
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
