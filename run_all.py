
"""
유튜브 + 구글뉴스 + 네이버 뉴스 -> 통합 엑셀 1개 파일
"""

import os
import re
import json
import subprocess
import difflib
import sys
from datetime import datetime

# py 폴더를 모듈 경로에 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "py"))

# .env 로드 (현재 디렉토리 기준)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass

import pandas as pd

from aggro_analyzer import analyze_articles
from excel_reporter import export_to_js
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


def _is_similar(title1: str, title2: str) -> bool:
    """두 제목이 비슷한지 (difflib 사용, 50% 이상 유사)."""
    if not title1 or not title2:
        return False
    # 간단한 정규화 (공백 제거 등)
    t1 = re.sub(r"\s+", "", str(title1))
    t2 = re.sub(r"\s+", "", str(title2))
    return difflib.SequenceMatcher(None, t1, t2).ratio() >= 0.5


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


def _load_existing_data() -> list:
    """기존 data.js에서 JSON 데이터 로드."""
    try:
        # 프로젝트 루트 기준 data.js (현재 파일이 루트에 있음)
        root_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(root_dir, "web", "data.js")
        
        if not os.path.exists(data_path):
            return []
            
        with open(data_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # JS 변수 선언(const keywordData = ) 제거하고 JSON 파싱
        # 예: const keywordData = [...];
        match = re.search(r"const\s+keywordData\s*=\s*(\[.*\]);", content, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        return []
    except Exception as e:
        print(f"[경고] 기존 데이터 로드 실패: {e}")
        return []


def _collect_with_auto_expand(scraper_func, min_results=5, **kwargs):
    """
    자동 기간 확장 수집: 1일 → 3일 → 7일 → 30일
    최소 min_results개 이상 수집될 때까지 기간 확장.
    
    Args:
        scraper_func: 스크래퍼 함수 (days_back 파라미터 지원 필요)
        min_results: 최소 결과 개수 (기본 5개)
        **kwargs: 스크래퍼 함수에 전달할 추가 인자
    
    Returns:
        수집된 결과 리스트
    """
    date_ranges = [1, 3, 7, 30]  # 오늘 → 3일 → 1주 → 1개월
    
    for days_back in date_ranges:
        try:
            results = scraper_func(days_back=days_back, **kwargs)
            if len(results) >= min_results:
                if days_back > 1:
                    print(f"    (기간 확장: {days_back}일)")
                return results
        except Exception:
            continue
    
    # 모든 시도 실패 시 마지막 시도 결과 반환 (빈 리스트일 수 있음)
    try:
        return scraper_func(days_back=30, **kwargs)
    except Exception:
        return []


def main() -> None:
    """유튜브·구글·네이버 수집 → 어그로 점수 → 엑셀 1개 파일."""
    all_items = []

    from aggro_keywords import SEARCH_TOPICS, AGGRO_DICTIONARY
    
    
    # 스크래퍼 상태 추적
    scraper_status = {"youtube": "OK", "google": "OK", "naver": "OK"}

    # 사용자 선택
    print("\n[주제 선택]")
    topics = list(SEARCH_TOPICS.keys()) # ['정치', '경제', '사회', '이슈', '장년']
    for i, topic in enumerate(topics):
        print(f"{i+1}. {topic}")
    
    try:
        choice = int(input("\n번호를 입력하세요: "))
        if 1 <= choice <= len(topics):
            selected_category = topics[choice - 1]
            # 기본적으로 사전(dictionary)에 있는 키워드 우선 사용
            # + '뉴스' 키워드도 추가해서 포괄적 수집
            base_keywords = SEARCH_TOPICS.get(selected_category, [])
            selected_keywords = base_keywords + [selected_category, f"{selected_category} 뉴스"]
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
        yt = _collect_with_auto_expand(
            scrape_youtube,
            min_results=5,
            max_per_query=3,
            max_total=10,
            query_list=selected_keywords
        )
        scored_yt = analyze_articles(yt, title_key="title")
        for item in scored_yt:
            row = _to_row(item, "유튜브")
            row["카테고리"] = selected_category
            all_items.append(row)
        print(f"    → {len(scored_yt)}건")
    except Exception as e:
        err_msg = str(e)
        print(f"    → 건너뜀 (오류: {err_msg})")
        scraper_status["youtube"] = "수집 불가 (API 오류 등)"

    # 2. 구글 뉴스
    try:
        print(f"  구글 뉴스 수집 중...")
        google = _collect_with_auto_expand(
            scrape_google_news,
            min_results=5,
            max_per_query=5,
            max_total=10,
            query_list=selected_keywords
        )
        scored_google = analyze_articles(google, title_key="title")
        for item in scored_google:
            row = _to_row(item, "구글뉴스")
            row["카테고리"] = selected_category
            all_items.append(row)
        print(f"    → {len(scored_google)}건")
    except Exception as e:
        err_msg = str(e)
        print(f"    → 건너뜀 (오류: {err_msg})")
        scraper_status["google"] = "수집 불가"

    # 3. 네이버 뉴스
    try:
        print(f"  네이버 뉴스 수집 중...")
        naver_section_map = {
            "정치": "100", "경제": "101", "사회": "102", 
            "장년": "103", # 생활/문화
        }
        sid1 = naver_section_map.get(selected_category, "100")
        
        naver = scrape_ranking_news(
            economy_count=5, 
            society_count=5, 
            total_limit=10, 
            sid1=sid1,
            query_list=selected_keywords  # API 사용시에도 해당 카테고리로 검색
        )  
        
        scored_naver = analyze_articles(naver, title_key="title")
        for item in scored_naver:
            row = _to_row(item, "네이버뉴스")
            row["카테고리"] = selected_category
            all_items.append(row)
        print(f"    → {len(scored_naver)}건")
    except Exception as e:
        err_msg = str(e)
        print(f"    → 건너뜀 (오류: {err_msg})")
        scraper_status["naver"] = "수집 불가"

    if not all_items:
        print("수집된 데이터가 없습니다. .env에 YOUTUBE_API_KEY를 확인하고, feedparser를 설치했는지 확인하세요.")
        return

    # 6. 엑셀 출력 & 웹용 JS 출력
    # (카테고리별로 모은 전체 데이터를 점수순 정렬)
    
    # [수정] 기존 데이터 병합 로직
    # 1. 기존 데이터 로드
    existing_data = _load_existing_data()
    
    # 2. 현재 수집한 카테고리의 기존 데이터 삭제 (업데이트)
    # 카테고리가 없는 데이터는 '정치'로 간주하거나 유지? -> 일단 유지
    final_items = [item for item in existing_data if item.get("카테고리") != selected_category]
    
    # 3. 새 데이터 추가
    # 새 데이터도 포맷팅 필요 (all_items는 딕셔너리 리스트)
    # _to_row 시점에서 이미 카테고리는 들어있음.
    
    # 점수 정렬 및 보강은 '이번에 수집한 데이터'에 대해서만? 아니면 전체?
    # -> 보강(_enrich)은 이번 수집 데이터에 대해서만 수행하고, 합치는 게 효율적.
    
    df_new = pd.DataFrame(all_items)
    if not df_new.empty:
        df_new["추천점수"] = pd.to_numeric(df_new["score"], errors="coerce").fillna(0)
        df_new = df_new.sort_values(by="추천점수", ascending=False)
        
        # 상위 30개 + 비슷한 뉴스 보강
        df_new = df_new.head(30).copy()
        df_new = _enrich_with_similar_news(df_new, all_items)
        
        # DataFrame -> Dict List 변환
        # export_to_js 내부에서 컬럼 매핑 등을 수행하므로, 여기서는 그냥 합쳐서 넘기는 게 복잡함.
        # export_to_js가 DataFrame을 받으니, 기존 데이터도 DF로 변환해서 합치는 게 낫다.
        
        # 기존 데이터 DF 변환
        if existing_data:
             df_old = pd.DataFrame(existing_data)
        else:
             df_old = pd.DataFrame()

        # 병합: (Existing - CurrentCat) + New
        # existing_data는 이미 필터링 됨 (final_items)
        df_final = pd.DataFrame(final_items)
        
        # 컬럼 매핑 주의: existing_data는 이미 한글 컬럼명("제목", "추천점수" 등)
        # df_new는 영문 컬럼명("title", "score" 등) 혼재 가능성 -> _ensure_columns가 처리함.
        # 하지만 df_new는 _enrich_with_similar_news 거치면서 일부 한글 컬럼("뉴스기사2_URL" 등) 생성됨.
        # 가장 깔끔한 방법: df_new를 export_to_js 로직과 유사하게 정규화한 뒤 합치기.
        
        # 편의상: df_new를 export_to_js에 넘기되, 'append_mode'를 지원하거나
        # 여기서 다 합쳐서 넘기거나.
        # export_to_js는 '순위'를 재매김. 카테고리별 순위? 아니면 전체 순위?
        # 웹 UI는 카테고리별로 필터링해서 보여주므로, 전체 리스트에 순위는 의미가 적음(보여줄 때 다시 매김).
        # 다만 export_to_js가 순위를 매겨버림.
        
        # 결론: df_new와 df_final(기존)을 합쳐서 df_merged를 만들고 export_to_js 호출.
        # 단, df_final의 컬럼 이름은 "제목", "카테고리" 등 한글.
        # df_new의 컬럼 이름은 "title", "category" 등 영문.
        # -> pd.concat 시 컬럼 불일치 발생.
        
        # 해결: df_new의 컬럼명을 한글로 매핑한 뒤 병합.
        from excel_reporter import _ensure_columns
        df_new_mapped = _ensure_columns(df_new)
        # _ensure_columns는 OUTPUT_COLUMNS_BASE(한글)만 남김.
        # 단, '카테고리'가 _ensure_columns 로직에 추가되어 있어야 함. (앞 단계에서 추가했음)
        
        # df_final(기존)은 이미 한글 컬럼.
        # 두 DF 병합
        df_merged = pd.concat([df_final, df_new_mapped], ignore_index=True)
        
        json_path = export_to_js(df_merged, scraper_status=scraper_status)
        print(f"웹 데이터 파일 업데이트 완료: {json_path}")
        print(f"총 {len(df_merged)}건 (누적)")

    else:
        print("이번 실행에서 수집된 데이터가 없습니다. 기존 데이터 유지.")
        # 수집 실패해도 기존 데이터는 유지하고 status만 업데이트 필요할 수 있음.
        # 여기서는 간단히 패스.


    # 7. 깃허브 자동 푸시
    git_push()


def git_push():
    """데이터 생성 후 깃허브에 자동 푸시"""
    print("\n[Git] 깃허브 자동 푸시 시작...")
    try:
        # 프로젝트 루트로 이동 (현재 파일이 루트에 있음)
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
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
