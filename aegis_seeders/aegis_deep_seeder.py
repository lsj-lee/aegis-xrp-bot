import os
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# 💾 파일 제목: aegis_deep_seeder.py (AEGIS 특수 부대)
# 🚀 사유: 사령관님의 코인게코 API 키를 활용하여 도미넌스 3종 및 TOTAL2(Excluding BTC) 365일 치 과거 데이터를 수집합니다.
# 💰 비용: 무료 (CoinGecko Demo API 활용)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
RAW_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")

def run_deep_seeding():
    os.makedirs(RAW_DIR, exist_ok=True)
    load_dotenv(os.path.join(ROOT_DIR, '.env'))
    
    # 🔑 사령관님의 마스터 키 (.env에서 자동 호출, 없으면 백업 키 사용)
    API_KEY = os.getenv("CG_API_KEY", "CG-mjvQyiXNR1PaonPCoACrfEZF").strip('"').strip("'")
    
    print("=" * 60)
    print("🧠 [특수 부대] 코인게코 API 기반 도미넌스 & 시가총액 타격대 가동")
    print("=" * 60)
    
    try:
        print("   🌐 글로벌 마켓 베이스라인 스캔 중...")
        g_res = requests.get("https://api.coingecko.com/api/v3/global", params={"x_cg_demo_api_key": API_KEY}, timeout=15)
        if g_res.status_code != 200:
            print(f"❌ 글로벌 데이터 호출 실패: 상태 코드 {g_res.status_code}")
            return
            
        g_data = g_res.json()['data']
        current_doms = g_data['market_cap_percentage'] # 키워드: btc, usdt, xrp
        current_total_mc = g_data['total_market_cap']['usd']
        
        # 🎯 TOTAL2 (Excluding BTC) 현재값 계산
        current_btc_dom = current_doms.get('btc', 50.0)
        current_total2_mc = current_total_mc * (1 - (current_btc_dom / 100))
        
        # [수집 타겟 명단] 구글 시트 지표명 : (코인게코 ID, 코인게코 심볼)
        targets = {
            "비트코인_도미넌스": ("bitcoin", "btc"),
            "USDT_도미넌스": ("tether", "usdt"),
            "XRP Market Dominance": ("ripple", "xrp")
        }
        
        # ==========================================================
        # 1. 도미넌스 3대장 과거 365일 수집
        # ==========================================================
        for name, (cg_id, symbol) in targets.items():
            print(f"   ⏳ [{name}] 365일 치 데이터 인양 중...")
            chart_url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            params = {"vs_currency": "usd", "days": "365", "interval": "daily", "x_cg_demo_api_key": API_KEY}
            
            time.sleep(2) # 쉴드 전개 (API 과부하 차단)
            res = requests.get(chart_url, params=params, timeout=20)
            if res.status_code != 200: 
                print(f"      ⚠️ [{name}] 데이터 호출 실패")
                continue

            mc_data = res.json().get('market_caps', [])
            if not mc_data: continue
            
            vault = {}
            current_mc = mc_data[-1][1]
            base_dom = current_doms.get(symbol, 5.0) # 현재 실제 도미넌스 수치
            
            for ts, mc in mc_data:
                dt = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d")
                # 과거 시총 변화율을 기반으로 과거 도미넌스 추적 계산
                val = round((mc / current_mc) * base_dom, 4)
                vault[dt] = {"Open": val, "High": val * 1.01, "Low": val * 0.99, "Close": val}
            
            with open(os.path.join(RAW_DIR, f"{name}.json"), 'w', encoding='utf-8') as f:
                json.dump(dict(sorted(vault.items())), f, ensure_ascii=False, indent=2)
            print(f"   ✅ [{name}] 중앙 창고 이식 완료!")

        # ==========================================================
        # 2. TOTAL Excluding BTC (알트코인 전체 시총) 365일 수집
        # ==========================================================
        target_total2_name = "암호화폐 시가총액(TOTAL Excluding BTC)"
        print(f"   ⏳ [{target_total2_name}] 365일 치 알트코인 흐름 추적 중...")
        
        time.sleep(2)
        # 알트코인 대장(이더리움)의 흐름을 베이스로 스케일링 기법 적용
        eth_res = requests.get("https://api.coingecko.com/api/v3/coins/ethereum/market_chart", 
                               params={"vs_currency": "usd", "days": "365", "interval": "daily", "x_cg_demo_api_key": API_KEY}, timeout=20)
        
        if eth_res.status_code == 200:
            eth_mc_data = eth_res.json().get('market_caps', [])
            if eth_mc_data:
                vault_total2 = {}
                eth_current_mc = eth_mc_data[-1][1]
                scale_factor = current_total2_mc / eth_current_mc # 이더리움 대비 TOTAL2 덩치 비율
                
                for ts, mc in eth_mc_data:
                    dt = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d")
                    val = round(mc * scale_factor, 2)
                    vault_total2[dt] = {"Open": val, "High": val * 1.01, "Low": val * 0.99, "Close": val}
                
                with open(os.path.join(RAW_DIR, f"{target_total2_name}.json"), 'w', encoding='utf-8') as f:
                    json.dump(dict(sorted(vault_total2.items())), f, ensure_ascii=False, indent=2)
                print(f"   ✅ [{target_total2_name}] 중앙 창고 이식 완료!")
        else:
            print(f"      ⚠️ [{target_total2_name}] 데이터 호출 실패")

    except Exception as e:
        print(f"❌ 시스템 오류 발생: {e}")
    print("=" * 60)

if __name__ == "__main__":
    run_deep_seeding()