import os
import json
from datetime import datetime, timedelta

# 💾 파일 제목: aegis_seeders/aegis_roadmap_seeder.py

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
RAW_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")

def run_roadmap_seeder():
    os.makedirs(RAW_DIR, exist_ok=True)
    print("=" * 60)
    print("🗺️ [역사 재건] 2026 로드맵 기대감 무제한(Max: 2000일) 구축 부대 가동")
    
    vault = {}
    today = datetime.now()
    MAX_DAYS = 2000 # 365일 족쇄 해제 -> 2000일
    
    # 5.5년 전의 무관심(10점)에서 현재의 기대감(70점)으로 진화하는 과정
    start_score = 10.0
    end_score = 70.0
    daily_increment = (end_score - start_score) / MAX_DAYS

    for i in range(MAX_DAYS, -1, -1):
        target_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        current_score = round(start_score + (daily_increment * (MAX_DAYS - i)), 4)
        
        vault[target_date] = {
            "Open": current_score, "High": current_score,
            "Low": current_score, "Close": current_score
        }

    with open(os.path.join(RAW_DIR, "2026_로드맵.json"), 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(vault.items())), f, ensure_ascii=False, indent=2)
    print(f"   ✅ [2026_로드맵] {MAX_DAYS}일 치 장기 상승 시계열 중앙 창고 이식 완료!")
    print("=" * 60)

if __name__ == "__main__":
    run_roadmap_seeder()