"""
유튜브 검색 스크래퍼 (YouTube Data API v3)
키워드 조합 검색, 7일 이내 + 10만 회 이상 영상 수집
"""

import os
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote_plus

import requests

# 검색 키워드 조합 (키워드 사전 기반)
SEARCH_QUERIES = [
    "한국 국산화 성공",
    "일본 패닉",
    "세계 최초",
    "국세청 조사",
    "폭락",
    "몰락",
]

# 7일 이내, 10만 회 이상
DAYS_BACK = 7
MIN_VIEWS = 100_000


def _get_api_key() -> str:
    """환경 변수에서 API 키 로드."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError(
            ".env 파일에 YOUTUBE_API_KEY를 설정하세요. "
            "Google Cloud Console에서 YouTube Data API v3 키를 발급받을 수 있습니다."
        )
    return key.strip()


def _search_youtube(api_key: str, query: str, max_results: int = 10) -> List[dict]:
    """키워드로 유튜브 검색."""
    published_after = (datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%dT00:00:00Z")
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "publishedAfter": published_after,
        "relevanceLanguage": "ko",
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        video_ids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        if not video_ids:
            return []
        return _get_video_details(api_key, video_ids)
    except requests.RequestException as e:
        print(f"[유튜브] 검색 오류 (query={query}): {e}")
        return []


def _get_video_details(api_key: str, video_ids: List[str]) -> List[dict]:
    """영상 상세(조회수, 업로드일) 조회."""
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": ",".join(video_ids[:50]),
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", []):
            vid = item.get("id", "")
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            views = int(stats.get("viewCount", 0))
            if views < MIN_VIEWS:
                continue
            published = snippet.get("publishedAt", "")[:10] if snippet.get("publishedAt") else ""
            results.append({
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "source": "유튜브",
                "views": views,
                "upload_date": published,
            })
        return results
    except requests.RequestException as e:
        print(f"[유튜브] 상세 조회 오류: {e}")
        return []


def scrape_youtube(max_per_query: int = 5, max_total: int = 30) -> List[dict]:
    """
    키워드 조합으로 유튜브 검색 (7일 이내, 10만 회 이상).

    Returns:
        [{"title": str, "url": str, "source": "유튜브", "views": int, "upload_date": str}, ...]
    """
    api_key = _get_api_key()
    seen_urls = set()
    results = []

    for query in SEARCH_QUERIES:
        if len(results) >= max_total:
            break
        items = _search_youtube(api_key, query, max_results=max_per_query)
        for item in items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                results.append(item)
            if len(results) >= max_total:
                break

    return results[:max_total]
