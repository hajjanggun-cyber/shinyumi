"""
엑셀 리포터 실행 스크립트
샘플 데이터로 엑셀 출력을 테스트합니다.
"""

import pandas as pd

from excel_reporter import export_to_excel

# 샘플 데이터 (실제로는 수집기·분석기에서 전달)
SAMPLE_DATA = [
    {
        "title": "일본 패닉... 미국도 경악한 한국의 세계 최초 국산화 성공",
        "score": 14.2,
        "source": "유튜브",
        "youtube_url": "https://www.youtube.com/watch?v=example1",
        "news_url": "",
        "views": 1250000,
        "upload_date": "2025-01-28",
    },
    {
        "title": "국세청 조사 3국, 33년 성역 무너졌다",
        "score": 12.8,
        "source": "네이버뉴스",
        "youtube_url": "",
        "news_url": "https://news.naver.com/article/12345",
        "views": "",
        "upload_date": "2025-01-30",
    },
    {
        "title": "처참한 몰락... 유령도시가 된 강남",
        "score": 11.5,
        "source": "구글뉴스",
        "youtube_url": "",
        "news_url": "https://news.google.com/articles/abc123",
        "views": "",
        "upload_date": "2025-01-29",
    },
    {
        "title": "IMF 경고, 전액 손실 가능성",
        "score": 10.1,
        "source": "유튜브",
        "youtube_url": "https://www.youtube.com/watch?v=example2",
        "news_url": "",
        "views": 890000,
        "upload_date": "2025-01-27",
    },
    {
        "title": "깡통 전세 폐업 속출, 카푸어의 눈물",
        "score": 8.3,
        "source": "네이버뉴스",
        "youtube_url": "",
        "news_url": "https://news.naver.com/article/67890",
        "views": "",
        "upload_date": "2025-01-31",
    },
]


def main() -> None:
    """샘플 데이터로 엑셀 파일 생성."""
    try:
        df = pd.DataFrame(SAMPLE_DATA)
        path = export_to_excel(df)
        print(f"엑셀 파일 생성 완료: {path}")
    except Exception as e:
        print(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
