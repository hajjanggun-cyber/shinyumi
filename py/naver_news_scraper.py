"""
네이버 뉴스 수집 (스크래핑 + API 병행)
- 스크래핑: '가장 많이 본 뉴스' 경제/사회 섹션 (인증 불필요)
- API: 뉴스 검색 API (Client ID + Secret 있으면 추가 수집)
"""

import os
import re
from email.utils import parsedate_to_datetime
from typing import List
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 섹션 코드: 경제=101, 사회=102
RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
SECTION_ECONOMY = 101
SECTION_SOCIETY = 102

# API 검색 키워드 (구글/유튜브와 동일)
SEARCH_QUERIES = ["급락", "단독", "최초", "국세청", "폭락"]

NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def _strip_html(text: str) -> str:
    """HTML 태그 제거."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


# ========== 스크래핑 (가장 많이 본 뉴스) ==========


def _fetch_ranking_page(sid1: int) -> str:
    """랭킹 페이지 HTML 조회."""
    try:
        resp = requests.get(RANKING_URL, params={"sid1": sid1}, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 뉴스 페이지 조회 실패 (sid1={sid1}): {e}") from e


def _extract_from_html(html: str, limit: int = 20) -> List[dict]:
    """HTML에서 기사 제목과 URL 추출."""
    soup = BeautifulSoup(html, "html.parser")
    seen_urls = set()
    articles = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "n.news.naver.com/article" not in href or "ntype=RANKING" not in href:
            continue

        url = urljoin("https://news.naver.com", href)
        if url in seen_urls:
            continue

        title = (a.get_text(strip=True) or "").strip()
        if len(title) < 5 or title in ("동영상기사", "이미지", "집계안내", "닫기"):
            continue

        seen_urls.add(url)
        articles.append({"title": title, "url": url, "source": "네이버뉴스", "section": ""})
        if len(articles) >= limit:
            break

    return articles


# ========== API (뉴스 검색) ==========


def _fetch_naver_api(client_id: str, client_secret: str, query: str, display: int = 10) -> List[dict]:
    """네이버 뉴스 검색 API 호출."""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": min(display, 100), "sort": "date"}

    try:
        resp = requests.get(NAVER_NEWS_API, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        results = []
        for item in items:
            title = _strip_html(item.get("title", ""))
            url = item.get("link") or item.get("originallink", "")
            raw_pub = item.get("pubDate") or ""
            upload_date = ""
            if raw_pub:
                try:
                    dt = parsedate_to_datetime(raw_pub)
                    upload_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    if len(raw_pub) >= 10 and raw_pub[4] == "-":
                        upload_date = raw_pub[:10]
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "source": "네이버뉴스",
                    "section": "API",
                    "upload_date": upload_date,
                })
        return results
    except Exception:
        return []


# ========== 통합 ==========


def scrape_ranking_news(
    economy_count: int = 10,
    society_count: int = 10,
    total_limit: int = 30,
) -> List[dict]:
    """
    스크래핑 + API 병행 수집.
    API 키 있으면 둘 다 사용, 없으면 스크래핑만.

    Returns:
        [{"title": str, "url": str, "source": "네이버뉴스", "section": str}, ...]
    """
    seen_urls = set()
    results = []

    # 1. 스크래핑 (가장 많이 본 뉴스) - 항상
    try:
        html_econ = _fetch_ranking_page(SECTION_ECONOMY)
        for item in _extract_from_html(html_econ, economy_count):
            item["section"] = "경제"
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                results.append(item)
            if len(results) >= total_limit:
                return results[:total_limit]

        html_soc = _fetch_ranking_page(SECTION_SOCIETY)
        for item in _extract_from_html(html_soc, society_count):
            item["section"] = "사회"
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                results.append(item)
            if len(results) >= total_limit:
                return results[:total_limit]
    except Exception as e:
        print(f"[네이버] 스크래핑 오류: {e}")

    # 2. API (키 있으면 추가)
    client_id = (os.getenv("NAVER_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("NAVER_CLIENT_SECRET") or "").strip()

    if client_id and client_secret:
        for query in SEARCH_QUERIES:
            if len(results) >= total_limit:
                break
            for item in _fetch_naver_api(client_id, client_secret, query, display=5):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    results.append(item)
                if len(results) >= total_limit:
                    break

    return results[:total_limit]
