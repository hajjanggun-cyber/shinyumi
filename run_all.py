"""
유튜브 + 구글뉴스 + 네이버 뉴스 → 통합 엑셀 1개 파일
"""

import os
import re

# .env 로드 (프로젝트 루트 기준)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass

import pandas as pd

from aggro_analyzer import analyze_articles
from excel_reporter import export_to_excel, export_to_json
from google_news_scraper import scrape_google_news
from naver_news_scraper import scrape_ranking_news
from youtube_scraper import scrape_youtube


def _to_row(item: dict, source_type: str) -> dict:
    """소스별 통일된 행 형식으로 변환."""
    base = {
        "title": item.get("title", ""),
        "score": item.get("score", 0),
        "score_keywords": item.get("score_keywords", ""),
        "source": source_type if source_type == "유튜브" else item.get("source", source_type),
        "youtube_url": item.get("url", "") if source_type == "유튜브" else "",
        "news_url": "" if source_type == "유튜브" else item.get("url", ""),
        "views": item.get("views", ""),
        "upload_date": item.get("upload_date", item.get("section", "")),
    }
    if source_type == "유튜브":
        base["source"] = "유튜브"
    return base


def _title_words(title: str) -> set:
    """제목에서 유의미한 단어(2자 이상) 추출."""
    if not title or not isinstance(title, str):
        return set()
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", str(title))
    return set(w for w in words if len(w) >= 2)


def _is_similar(title1: str, title2: str, min_common: int = 2) -> bool:
    """두 제목이 비슷한지 (공통 단어 2개 이상)."""
    w1, w2 = _title_words(title1), _title_words(title2)
    return len(w1 & w2) >= min_common


def _enrich_with_similar_news(df: pd.DataFrame, all_news: list) -> pd.DataFrame:
    """뉴스 행에 비슷한 기사 최대 2개 추가 (뉴스기사2_URL, 뉴스기사2_날짜, 뉴스기사3_URL, 뉴스기사3_날짜)."""
    out = df.copy()
    out["뉴스기사2_URL"] = ""
    out["뉴스기사2_날짜"] = ""
    out["뉴스기사3_URL"] = ""
    out["뉴스기사3_날짜"] = ""

    news_pool = [
        (r.get("news_url", "") or r.get("뉴스기사_URL", ""), r.get("upload_date", "") or r.get("업로드일", ""), r.get("title", ""))
        for r in all_news
        if (r.get("news_url") or r.get("뉴스기사_URL")) and (r.get("title") or "")
    ]

    for idx, row in out.iterrows():
        news_url = row.get("뉴스기사_URL", "") or row.get("news_url", "")
        if not news_url or not str(news_url).strip():
            continue
        title = row.get("제목", "") or row.get("title", "")
        used_urls = {str(news_url).strip()}
        similar = []
        for url, udate, t in news_pool:
            if not url or str(url).strip() in used_urls:
                continue
            if _is_similar(title, t):
                similar.append((url, udate))
                used_urls.add(str(url).strip())
                if len(similar) >= 2:
                    break
        if similar:
            out.at[idx, "뉴스기사2_URL"] = similar[0][0]
            out.at[idx, "뉴스기사2_날짜"] = similar[0][1]
            if len(similar) >= 2:
                out.at[idx, "뉴스기사3_URL"] = similar[1][0]
                out.at[idx, "뉴스기사3_날짜"] = similar[1][1]
    return out


def main() -> None:
    """유튜브·구글·네이버 수집 → 어그로 점수 → 엑셀 1개 파일."""
    all_items = []

    # 1. 유튜브
    try:
        print("유튜브 수집 중...")
        yt = scrape_youtube(max_per_query=5, max_total=15)
        scored_yt = analyze_articles(yt, title_key="title")
        for item in scored_yt:
            all_items.append(_to_row(item, "유튜브"))
        print(f"  → {len(scored_yt)}건")
    except Exception as e:
        print(f"  → 건너뜀 (오류: {e})")

    # 2. 구글 뉴스 (RSS + NewsAPI 병행)
    try:
        print("구글 뉴스 수집 중 (RSS + NewsAPI)...")
        google = scrape_google_news(max_per_query=10, max_total=25)
        scored_google = analyze_articles(google, title_key="title")
        for item in scored_google:
            all_items.append(_to_row(item, "구글뉴스"))
        print(f"  → {len(scored_google)}건")
    except Exception as e:
        print(f"  → 건너뜀 (오류: {e})")

    # 3. 네이버 뉴스 (스크래핑 + API 병행)
    try:
        print("네이버 뉴스 수집 중 (스크래핑 + API)...")
        naver = scrape_ranking_news(economy_count=10, society_count=10, total_limit=30)
        scored_naver = analyze_articles(naver, title_key="title")
        for item in scored_naver:
            all_items.append(_to_row(item, "네이버뉴스"))
        print(f"  → {len(scored_naver)}건")
    except Exception as e:
        print(f"  → 건너뜀 (오류: {e})")

    if not all_items:
        print("수집된 데이터가 없습니다. .env에 YOUTUBE_API_KEY를 확인하고, feedparser를 설치했는지 확인하세요.")
        return

    # 4. 추천점수 기준 정렬
    df = pd.DataFrame(all_items)
    df["추천점수"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    df = df.sort_values(by="추천점수", ascending=False)

    # 5. 상위 30위까지 비슷한 뉴스 기사 보강 (뉴스기사2,3 URL·날짜)
    df_top = df.head(30).copy()
    df_top = _enrich_with_similar_news(df_top, all_items)

    # 6. 엑셀 출력 & 웹용 JSON 출력
    path = export_to_excel(df_top)
    print(f"\n엑셀 파일 생성 완료: {path}")

    json_path = export_to_json(df_top)
    print(f"웹 데이터 파일 생성 완료: {json_path}")
    
    print(f"총 {len(df_top)}건 (유튜브·구글·네이버 통합)")


if __name__ == "__main__":
    main()
