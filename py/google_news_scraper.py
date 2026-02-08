"""
구글 뉴스 수집 (RSS + NewsAPI.org 병행)
- RSS: 무료, API 키 불필요
- NewsAPI: API 키 있으면 추가 수집 (더 다양한 기사)
"""

import os
import time
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote_plus

import requests

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 검색 키워드 (실시간 경제, 시사)
SEARCH_QUERIES = ["급락", "단독", "최초", "국세청", "폭락"]

RSS_BASE = "https://news.google.com/rss/search"
NEWSAPI_URL = "https://newsapi.org/v2/everything"


def _fetch_rss(query: str, max_results: int = 15) -> List[dict]:
    """구글 뉴스 RSS에서 기사 수집 (무료, API 키 불필요)."""
    if feedparser is None:
        return []

    url = f"{RSS_BASE}?q={quote_plus(query)}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        results = []
        for entry in feed.get("entries", [])[:max_results]:
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or entry.get("id", "")
            pub_parsed = entry.get("published_parsed")
            published = time.strftime("%Y-%m-%d", pub_parsed) if pub_parsed else ""
            if title and len(title) > 3:
                results.append({
                    "title": title,
                    "url": link,
                    "source": "구글뉴스",
                    "views": "",
                    "upload_date": published,
                })
        return results
    except Exception:
        return []


def _fetch_newsapi(api_key: str, query: str, max_results: int = 10) -> List[dict]:
    """NewsAPI.org에서 기사 수집 (API 키 필요)."""
    from_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "apiKey": api_key,
        "from": from_date,
        "sortBy": "publishedAt",
        "pageSize": min(max_results, 100),
    }
    try:
        resp = requests.get(NEWSAPI_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return []
        results = []
        for article in data.get("articles", []):
            title = (article.get("title") or "").strip()
            url = article.get("url", "")
            published = (article.get("publishedAt") or "")[:10]
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "source": "구글뉴스",
                    "views": "",
                    "upload_date": published,
                })
        return results
    except Exception:
        return []


def scrape_google_news(max_per_query: int = 10, max_total: int = 50) -> List[dict]:
    """
    RSS + NewsAPI 병행 수집.
    API 키 있으면 둘 다 사용, 없으면 RSS만 사용.

    Returns:
        [{"title": str, "url": str, "source": "구글뉴스", ...}, ...]
    """
    seen_urls = set()
    results = []

    # 1. RSS (항상 시도)
    for query in SEARCH_QUERIES:
        if len(results) >= max_total:
            break
        for item in _fetch_rss(query, max_results=max_per_query):
            url = item.get("url", "") or item.get("title", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(item)
            if len(results) >= max_total:
                break

    # 2. NewsAPI (키 있으면 추가)
    api_key = (os.getenv("NEWS_API_KEY") or "").strip()
    if api_key:
        for query in SEARCH_QUERIES:
            if len(results) >= max_total:
                break
            for item in _fetch_newsapi(api_key, query, max_results=5):
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(item)
                if len(results) >= max_total:
                    break

    return results[:max_total]
