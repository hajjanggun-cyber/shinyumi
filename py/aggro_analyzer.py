"""
어그로 분석기
제목에 키워드가 포함된 경우 등급별 가중치로 점수 부여
"""

from typing import List, Tuple

from keyword_dict import AGGRO_DICTIONARY


def calculate_aggro_score(title: str) -> Tuple[float, List[str]]:
    """
    제목에 대한 어그로 점수 및 기여 키워드 계산.
    S급×3, A급×2, B급×1.5 가중치 적용.

    Args:
        title: 검사할 제목

    Returns:
        (어그로 점수, 점수에 기여한 키워드 리스트)
    """
    if not title or not isinstance(title, str):
        return 0.0, []

    score = 0.0
    matched_keywords: List[str] = []
    title_lower = title

    for grade, data in AGGRO_DICTIONARY.items():
        weight = data["weight"]
        keywords = data["keywords"]

        for kw in keywords:
            if kw and kw in title_lower:
                score += weight
                matched_keywords.append(kw)

    return round(score, 2), matched_keywords


def analyze_articles(articles: List[dict], title_key: str = "title") -> List[dict]:
    """
    기사 리스트에 어그로 점수 및 기여 키워드 부여.

    Args:
        articles: [{"title": str, "url": str, ...}, ...]
        title_key: 제목 필드명

    Returns:
        각 항목에 "score", "score_keywords" 추가된 리스트 (점수 높은 순 정렬)
    """
    result = []
    for item in list(articles):
        row = dict(item)
        score, matched = calculate_aggro_score(row.get(title_key, ""))
        row["score"] = score
        row["score_keywords"] = ", ".join(matched) if matched else ""
        result.append(row)

    result.sort(key=lambda x: x.get("score", 0), reverse=True)
    return result
