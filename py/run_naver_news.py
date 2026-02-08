"""
네이버 뉴스 스크래핑 → 어그로 분석 → 엑셀 출력
"""

import pandas as pd

from aggro_analyzer import analyze_articles
from excel_reporter import export_to_excel
from naver_news_scraper import scrape_ranking_news


def main() -> None:
    """네이버 뉴스 20건 수집, 어그로 점수 부여, 엑셀 저장."""
    try:
        # 1. 네이버 뉴스 스크래핑 (경제 10 + 사회 10 = 20건)
        print("네이버 뉴스 수집 중...")
        articles = scrape_ranking_news(economy_count=10, society_count=10, total_limit=20)

        if not articles:
            print("수집된 기사가 없습니다.")
            return

        print(f"수집 완료: {len(articles)}건")

        # 2. 어그로 점수 부여
        print("어그로 점수 계산 중...")
        scored = analyze_articles(articles, title_key="title")

        # 3. 엑셀용 DataFrame 생성 (뉴스 URL 포함)
        rows = []
        for item in scored:
            rows.append({
                "title": item.get("title", ""),
                "score": item.get("score", 0),
                "source": item.get("source", "네이버뉴스"),
                "youtube_url": "",
                "news_url": item.get("url", ""),
                "views": "",
                "upload_date": item.get("section", ""),
            })
        df = pd.DataFrame(rows)

        # 4. 엑셀 출력
        path = export_to_excel(df)
        print(f"엑셀 파일 생성 완료: {path}")

    except Exception as e:
        print(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
