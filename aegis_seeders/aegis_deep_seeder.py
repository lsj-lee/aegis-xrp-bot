import os
import json
import requests
import time
from datetime import datetime

# 🚀 사령관님의 마스터 키
REAL_API_KEY = "CG-mjvQyiXNR1PaonPCoACrfEZF"

# 🧭 절대 경로 레이더: 현재 파일 위치에서 한 칸 위(부모)로 올라가서 aegis_data를 찾음
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
RAW_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")

def run_deep_seeding():
    os.makedirs(RAW_DIR, exist_ok=True)
    print("=" * 60)
    print("🧠 [초기 인양] 코인게코 365일 도미넌스 타격대 가동")
    
    targets = {"비트코인_도미넌스": "bitcoin", "USDT_도미넌스": "tether"}
    try:
        g_res = requests.get("https://api.coingecko.com/api/v3/global", params={"x_cg_demo_api_key": REAL_API_KEY}, timeout=15)
        current_doms = g_res.json()['data']['market_cap_percentage']
        
        for name, cg_id in targets.items():
            print(f"   ⏳ [{name}] 365일 치 인양 중...")
            chart_url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            params = {"vs_currency": "usd", "days": "365", "interval": "daily", "x_cg_demo_api_key": REAL_API_KEY}
            
            time.sleep(3) 
            res = requests.get(chart_url, params=params, timeout=20)
            if res.status_code != 200: continue

            mc_data = res.json().get('market_caps', [])
            vault = {}
            current_mc = mc_data[-1][1]
            base_dom = current_doms.get(cg_id, 7.0)
            
            for ts, mc in mc_data:
                dt = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d")
                val = round((mc / current_mc) * base_dom, 4)
                vault[dt] = {"Open": val, "High": val + 0.05, "Low": val - 0.05, "Close": val}
            
            with open(os.path.join(RAW_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
                json.dump(dict(sorted(vault.items())), f, ensure_ascii=False, indent=2)
            print(f"   ✅ [{name}] 중앙 창고 이식 완료!")

    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
    print("=" * 60)

if __name__ == "__main__":
    run_deep_seeding()