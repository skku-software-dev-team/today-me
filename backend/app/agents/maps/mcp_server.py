"""Google Maps / Places API를 MCP 도구로 노출하는 FastMCP 서버.

장소 에이전트·맛집 에이전트가 공용으로 사용한다.
실행: python -m app.agents.maps.mcp_server
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("google-maps")

_PLACES_BASE = "https://places.googleapis.com/v1"
_GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode/json"


def _api_key() -> str:
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY 환경변수가 없습니다.")
    return key


@mcp.tool()
async def search_places(
    query: str,
    lat: float,
    lng: float,
    radius_meters: int = 2000,
    max_results: int = 5,
) -> list[dict]:
    """주변 장소를 텍스트 검색한다 (카페·공원·문화공간 등).

    Args:
        query: 검색어 (예: "감성 카페", "조용한 공원")
        lat: 위도
        lng: 경도
        radius_meters: 검색 반경 (미터)
        max_results: 최대 결과 수
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.googleMapsUri,places.primaryTypeDisplayName",
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
        "maxResultCount": max_results,
        "languageCode": "ko",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{_PLACES_BASE}/places:searchText", headers=headers, json=body)
        resp.raise_for_status()

    results = []
    for p in resp.json().get("places", []):
        results.append(
            {
                "name": p.get("displayName", {}).get("text", ""),
                "address": p.get("formattedAddress", ""),
                "rating": p.get("rating"),
                "review_count": p.get("userRatingCount"),
                "type": p.get("primaryTypeDisplayName", {}).get("text", ""),
                "maps_url": p.get("googleMapsUri", ""),
            }
        )
    return results


@mcp.tool()
async def search_restaurants(
    cuisine: str,
    lat: float,
    lng: float,
    radius_meters: int = 1500,
    max_results: int = 5,
) -> list[dict]:
    """주변 맛집을 음식 종류로 검색한다.

    Args:
        cuisine: 음식 종류 (예: "한식", "파스타", "라멘")
        lat: 위도
        lng: 경도
        radius_meters: 검색 반경 (미터)
        max_results: 최대 결과 수
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.googleMapsUri,places.primaryTypeDisplayName,places.editorialSummary",
    }
    body = {
        "textQuery": f"{cuisine} 맛집",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
        "maxResultCount": max_results,
        "languageCode": "ko",
        "includedType": "restaurant",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{_PLACES_BASE}/places:searchText", headers=headers, json=body)
        resp.raise_for_status()

    results = []
    for p in resp.json().get("places", []):
        results.append(
            {
                "name": p.get("displayName", {}).get("text", ""),
                "address": p.get("formattedAddress", ""),
                "rating": p.get("rating"),
                "review_count": p.get("userRatingCount"),
                "cuisine": p.get("primaryTypeDisplayName", {}).get("text", cuisine),
                "summary": p.get("editorialSummary", {}).get("text", ""),
                "maps_url": p.get("googleMapsUri", ""),
            }
        )
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
