import importlib

# 관리할 카테고리 모듈 리스트
MODULES = ["politics", "economy", "society", "senior"]
CATEGORY_MAP = {
    "politics": "정치",
    "economy": "경제",
    "society": "사회",
    "senior": "장년"
}

SEARCH_TOPICS = {}
KEYWORDS_TIER_1 = []
KEYWORDS_TIER_2 = []
KEYWORDS_TIER_3 = []

# 각 모듈에서 키워드 로드 및 통합
for mod_name in MODULES:
    try:
        # 상대 경로 임포트
        module = importlib.import_module(f".{mod_name}", package=__name__)
        
        # 검색 키워드 통합
        category_han = CATEGORY_MAP.get(mod_name)
        SEARCH_TOPICS[category_han] = getattr(module, "SEARCH_KEYWORDS", [])
        
        # 가산점 키워드 통합 (중복 허용 후 나중에 제거)
        KEYWORDS_TIER_1.extend(getattr(module, "TIER_1", []))
        KEYWORDS_TIER_2.extend(getattr(module, "TIER_2", []))
        KEYWORDS_TIER_3.extend(getattr(module, "TIER_3", []))
    except Exception as e:
        print(f"[오류] 키워드 모듈 로드 실패 ({mod_name}): {e}")

# 중복 제거 및 리스트 정규화
KEYWORDS_TIER_1 = list(set(KEYWORDS_TIER_1))
KEYWORDS_TIER_2 = list(set(KEYWORDS_TIER_2))
KEYWORDS_TIER_3 = list(set(KEYWORDS_TIER_3))

# 분석기용 사전 구성
AGGRO_DICTIONARY = {
    "Tier1": {"keywords": KEYWORDS_TIER_1, "weight": 10},
    "Tier2": {"keywords": KEYWORDS_TIER_2, "weight": 7},
    "Tier3": {"keywords": KEYWORDS_TIER_3, "weight": 3},
}
