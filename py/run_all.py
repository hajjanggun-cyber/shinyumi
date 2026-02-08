"""
유튜브 + 구글뉴스 + 네이버 뉴스 → 통합 엑셀 1개 파일
"""

import os
import re
import subprocess
from datetime import datetime

# .env 로드 (프로젝트 루트 기준)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    load_dotenv(_env_path)
except ImportError:
    pass

import pandas as pd

from aggro_analyzer import analyze_articles
from aggro_analyzer import analyze_articles
from excel_reporter import export_to_js
from google_news_scraper import scrape_google_news
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
        "category": item.get("category", ""), # 카테고리 필드 추가
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

    from keyword_dict import SEARCH_TOPICS, AGGRO_DICTIONARY
    
    
    # 사용자 선택
    print("\n[주제 선택]")
    topics = list(SEARCH_TOPICS.keys()) # ['정치', '경제', '사회', '이슈', '장년']
    for i, topic in enumerate(topics):
        print(f"{i+1}. {topic}")
    
    try:
        choice = int(input("\n번호를 입력하세요: "))
        if 1 <= choice <= len(topics):
            selected_category = topics[choice - 1]
            selected_keywords = SEARCH_TOPICS[selected_category]
        else:
            print("잘못된 번호입니다. 프로그램을 종료합니다.")
            return
    except ValueError:
        print("숫자를 입력해주세요. 프로그램을 종료합니다.")
        return

    print(f"\n=== [{selected_category}] 카테고리 수집 시작 ===")
    
    # 1. 유튜브
    try:
        print(f"  유튜브 수집 중 ({selected_keywords[:3]}...)")
        yt = scrape_youtube(max_per_query=3, max_total=10, query_list=selected_keywords)
        scored_yt = analyze_articles(yt, title_key="title")
        for item in scored_yt:
            row = _to_row(item, "유튜브")
            row["category"] = selected_category
            all_items.append(row)
        print(f"    → {len(scored_yt)}건")
    except Exception as e:
        print(f"    → 건너뜀 (오류: {e})")

    # 2. 구글 뉴스
    try:
        print(f"  구글 뉴스 수집 중...")
        google = scrape_google_news(max_per_query=5, max_total=10, query_list=selected_keywords)
        scored_google = analyze_articles(google, title_key="title")
        for item in scored_google:
            row = _to_row(item, "구글뉴스")
            row["category"] = selected_category
            all_items.append(row)
        print(f"    → {len(scored_google)}건")
    except Exception as e:
        print(f"    → 건너뜀 (오류: {e})")

    # 3. 네이버 뉴스
    try:
        print(f"  네이버 뉴스 수집 중...")
        naver_section_map = {
            "정치": "100", "경제": "101", "사회": "102", 
            "이슈": "104", # 세계/이슈
            "장년": "103", # 생활/문화
        }
        sid1 = naver_section_map.get(selected_category, "100")
        
        naver = scrape_ranking_news(economy_count=5, society_count=5, total_limit=10, sid1=sid1) 
        
        scored_naver = analyze_articles(naver, title_key="title")
        for item in scored_naver:
            row = _to_row(item, "네이버뉴스")
            row["category"] = selected_category
            all_items.append(row)
        print(f"    → {len(scored_naver)}건")
    except Exception as e:
        print(f"    → 건너뜀 (오류: {e})")

    if not all_items:
        print("수집된 데이터가 없습니다. .env에 YOUTUBE_API_KEY를 확인하고, feedparser를 설치했는지 확인하세요.")
        return

    # 6. 엑셀 출력 & 웹용 JS 출력
    # (카테고리별로 모은 전체 데이터를 점수순 정렬)
    df = pd.DataFrame(all_items)
    if not df.empty:
        df["추천점수"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
        df = df.sort_values(by="추천점수", ascending=False)

        # 상위 100개 + 비슷한 뉴스 보강 (개수 늘림)
        df_top = df.head(100).copy()
        df_top = _enrich_with_similar_news(df_top, all_items)

        # 엑셀 저장 로직 삭제됨
        # path = export_to_excel(df_top)
        # print(f"\n엑셀 파일 생성 완료: {path}")

        json_path = export_to_js(df_top)
        print(f"웹 데이터 파일 생성 완료: {json_path}")
        
        print(f"총 {len(df_top)}건 (전체 카테고리 통합)")
    else:
        print("수집된 데이터가 없습니다.")

    # 7. 깃허브 자동 푸시
    git_push()


def git_push():
    """데이터 생성 후 깃허브에 자동 푸시"""
    print("\n[Git] 깃허브 자동 푸시 시작...")
    try:
        # 프로젝트 루트로 이동 (현재 py/ 폴더에 있다면)
        # run_all.py가 py/ 안에 있으므로, 부모 디렉토리가 루트
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(script_dir)
        
        # 1. git add
        subprocess.run(["git", "add", "."], cwd=root_dir, check=True)
        
        # 2. git commit
        # 변경사항이 없으면 에러가 날 수 있으므로 check=False로 하고 출력만 확인하거나
        # status를 먼저 체크할 수도 있음. 여기서는 간단히 try로 감쌈.
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Auto: Update data files ({current_time})"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=root_dir, check=False)
        
        # 3. git push
        subprocess.run(["git", "push", "origin", "main"], cwd=root_dir, check=True)
        print("[Git] 푸시 완료!")
        
    except Exception as e:
        print(f"[Git] 푸시 실패: {e}")



if __name__ == "__main__":
    main()
