"""네이버 쇼핑 검색 API를 MCP 도구로 노출하는 FastMCP 서버.

에이전트가 stdio transport로 이 프로세스를 스폰해서 사용한다.
실행: python -m app.agents.style.mcp_server
"""

import os
import re

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("naver-shopping")

_NAVER_SHOPPING_URL = "https://openapi.naver.com/v1/search/shop.json"


def _headers() -> dict:
    client_id = os.environ.get("NAVER_CLIENT_ID", "")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경변수가 없습니다.")
    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }


@mcp.tool()
async def search_product(query: str, max_results: int = 3) -> list[dict]:
    """네이버 쇼핑에서 패션 상품을 검색한다.

    Args:
        query: 검색어 (예: "오버사이즈 후드 베이지", "와이드 린넨 팬츠")
        max_results: 최대 결과 수 (1~5)
    """
    try:
        headers = _headers()
    except RuntimeError:
        return []

    params = {"query": query, "display": min(max_results, 5), "sort": "sim"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_NAVER_SHOPPING_URL, headers=headers, params=params)
        resp.raise_for_status()

    results = []
    for item in resp.json().get("items", []):
        title = re.sub(r"<[^>]+>", "", item.get("title", ""))
        results.append(
            {
                "name": title,
                "product_url": item.get("link", ""),
                "image_url": item.get("image", ""),
                "price": item.get("lprice", ""),
                "mall": item.get("mallName", ""),
            }
        )
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
