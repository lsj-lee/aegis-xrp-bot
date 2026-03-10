import os
import json
import requests
import time
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
RAW_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")

def run_fng_harvest():
    os.makedirs(RAW_DIR, exist_ok=True)
    print("=" * 60)
    print("📡 [초기 인양] FNG 시장 심리 무제한(Max) 타격대 가동")
    
    url = "https://api.alternative.me/fng/?limit=0"
    try:
        res = requests.get(url, timeout=15)
        raw_data = res.json().get('data', [])
        
        vault = {}
        for entry in raw_data:
            dt = datetime.fromtimestamp(int(entry['timestamp'])).strftime("%Y-%m-%d")
            val = float(entry['value'])
            vault[dt] = {"Open": val, "High": val, "Low": val, "Close": val}
        
        save_path = os.path.join(RAW_DIR, "시장_심리_FNG.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(vault.items())), f, ensure_ascii=False, indent=2)
            
        print(f"   ✅ [시장_심리_FNG] {len(vault)}일 치 데이터 중앙 창고 이식 완료!")
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
    print("=" * 60)

if __name__ == "__main__":
    run_fng_harvest()