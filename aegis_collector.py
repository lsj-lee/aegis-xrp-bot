import os
import json
import time
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import pandas as pd
import requests
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

# 💾 파일 제목: aegis_collector.py (지능형 2-Track 통합 수집기 - 실록 연동 버전)
# 🚀 사유: 매일의 뉴스를 [고유/거시]로 분리하여 점수와 '분석 근거'를 실록에 누적 기록

load_dotenv()
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")
NEWS_ARCHIVE_DIR = os.path.join(ROOT_DIR, "aegis_data", "news_archive")
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(NEWS_ARCHIVE_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json'
}

def get_fallback_models():
    """시트의 무기 등급표를 읽어 타격 체인을 구성합니다."""
    try:
        creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        gc = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=scopes))
        settings_ws = gc.open("AEGIS_Daily_Report").worksheet("AEGIS_Settings")
        rows = settings_ws.get_all_values()
        chain = []
        for row in rows[1:4]: 
            if len(row) > 1 and row[1].strip(): chain.append(row[1].strip())
            if len(row) > 3 and row[3].strip(): chain.append(row[3].strip())
            if len(row) > 4 and row[4].strip(): chain.append(row[4].strip())
        return chain if chain else ["gemini-3.1-pro"]
    except: return ["gemini-3.1-pro"]

def requests_retry_get(url, retries=3, delay=2):
    for i in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            res.raise_for_status()
            return res
        except Exception:
            if i == retries - 1: return None
            time.sleep(delay)
    return None

def load_vault(name):
    path = os.path.join(RAW_DATA_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_vault(name, data):
    path = os.path.join(RAW_DATA_DIR, f"{name}.json")
    with open(path, 'w', encoding='utf-8') as f: 
        json.dump(dict(sorted(data.items())), f, ensure_ascii=False, indent=2)

def update_legal_archive(date_str, prefix, intelligence):
    """오늘의 뉴스 점수와 근거를 legal_events_history.json에 누적 병합합니다."""
    archive_path = os.path.join(NEWS_ARCHIVE_DIR, "legal_events_history.json")
    archive = {}
    if os.path.exists(archive_path):
        try:
            with open(archive_path, 'r', encoding='utf-8') as f: archive = json.load(f)
        except: pass
    
    if date_str not in archive:
        archive[date_str] = {}
        
    archive[date_str][f"{prefix}_score"] = float(intelligence.get('score', 50))
    archive[date_str][f"{prefix}_headline"] = intelligence.get('headline', '데이터 없음')
    archive[date_str][f"{prefix}_reason"] = intelligence.get('reason', '수집 실패 또는 통신 오류')

    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(archive.items())), f, ensure_ascii=False, indent=2)

def process_ai_intelligence(name, rule, fallback_chain):
    """고급 모델로 오늘의 뉴스를 분석하고 점수와 근거를 JSON으로 도출합니다."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    category = "리플(XRP) 고유 소송 및 기술 파트너십" if "리플" in name else "글로벌 거시 경제 및 주요 금융 정세"
    
    prompt = f"""
    당신은 최고급 AI 데이터 분석가입니다. 오늘 발생한 '{category}' 관련 주요 뉴스를 1개 선정하여 분석하십시오.
    기준: {rule}
    [임무]
    1. 이 뉴스가 리플(XRP) 가격에 미칠 영향을 0(재앙)~100(폭등) 사이의 숫자로 산출하십시오.
    2. 뉴스 한 줄 요약(headline)과 분석 근거(reason)를 명확히 작성하십시오.
    [포맷] 반드시 아래 순수 JSON 포맷으로만 응답하십시오 (백틱이나 마크다운 금지):
    {{"score": 숫자, "headline": "요약", "reason": "분석 근거 (2문장 이내)"}}
    """

    for model in fallback_chain:
        try:
            print(f"      ▶️ [{model}] 지능 가동 중...")
            response = client.models.generate_content(
                model=model, 
                contents=prompt, 
                config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json")
            )
            return json.loads(response.text)
        except APIError as e:
            print(f"      ⚠️ API 통신 문제({e.code}). 다음 순위 무기로 교체합니다.")
        except Exception:
            print(f"      ❌ 파싱 오류. 다음 순위 무기로 교체합니다.")
    
    return {"score": 50, "headline": "시스템 분석 실패", "reason": "모든 타격 체인 응답 불가"}

def process_live_to_vault(name, val, src_type, url, rule, fallback_chain):
    vault = load_vault(name)
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        final_score = 50.0
        if src_type == 'JSON_API':
            res = requests_retry_get(url)
            if res:
                temp = res.json()
                if rule:
                    for k in rule.split('.'): temp = temp[k]
                final_score = float(temp)
        elif src_type == 'AI_SCORE':
            intelligence = process_ai_intelligence(name, rule, fallback_chain)
            final_score = float(intelligence.get('score', 50.0))
            
            # 🎯 2-Track 실록 기록 (리플 vs 거시경제 판별)
            prefix = "xrp" if "리플" in name else "macro"
            update_legal_archive(today, prefix, intelligence)
            
        elif src_type == 'MANUAL': 
            final_score = float(val) if val else 50.0
        
        # 🎯 architect와 동일한 캔들 변동폭(±1.5) 적용으로 시계열 정합성 유지
        vault[today] = {
            "Open": final_score, 
            "High": round(final_score + 1.5, 2), 
            "Low": round(final_score - 1.5, 2), 
            "Close": final_score
        }
        save_vault(name, vault)
        return True
    except Exception as e: 
        print(f"   [디버그] {name} 수집 오류: {e}")
        return False

def fetch_yahoo_upbit_vault(name, ticker, src_type):
    vault = load_vault(name)
    precision = 8 if "도미넌스" in name or "BTC" in ticker else 4
    try:
        if src_type in ['YAHOO', 'YAHOO_VOL']:
            period_val = "max" if not vault else "5d"
            df = yf.download(ticker, period=period_val, progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
                for idx, row in df.iterrows():
                    dt_str = str(idx)[:10]
                    if src_type == 'YAHOO_VOL':
                        vol = float(row['Volume'])
                        if pd.isna(vol) or vol == 0: continue
                        vault[dt_str] = {"Open": vol, "High": vol, "Low": vol, "Close": vol}
                    else:
                        vault[dt_str] = {
                            "Open": round(float(row['Open']), precision),
                            "High": round(float(row['High']), precision),
                            "Low": round(float(row['Low']), precision),
                            "Close": round(float(row['Close']), precision)
                        }
        elif src_type == 'UPBIT':
            count_val = 200 if not vault else 10
            res = requests_retry_get(f"https://api.upbit.com/v1/candles/days?market={ticker}&count={count_val}")
            if res:
                for d in res.json():
                    vault[d['candle_date_time_utc'][:10]] = {
                        "Open": round(float(d['opening_price']), precision),
                        "High": round(float(d['high_price']), precision),
                        "Low": round(float(d['low_price']), precision),
                        "Close": round(float(d['trade_price']), precision)
                    }
    except Exception: return False
    if vault: save_vault(name, vault)
    return True

def fetch_fng_vault(name, rule):
    vault = load_vault(name)
    limit = '0' if not vault else '5'
    try:
        time.sleep(2) 
        res = requests_retry_get(f"https://api.alternative.me/fng/?limit={limit}")
        if res:
            data = res.json().get('data', [])
            for d in data:
                dt = datetime.fromtimestamp(int(d['timestamp'])).strftime("%Y-%m-%d")
                val = float(d['value'])
                vault[dt] = {"Open": val, "High": val, "Low": val, "Close": val}
            save_vault(name, vault)
            return True
    except: return False

def fetch_fred_direct(name, ticker):
    vault = load_vault(name)
    try:
        period_val = "max" if not vault else "5d"
        df = yf.download("^IRX", period=period_val, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            for idx, row in df.iterrows():
                dt_str = str(idx)[:10]
                val = row['Close']
                if pd.isna(val): continue
                vault[dt_str] = {
                    "Open": round(float(val), 8), "High": round(float(val), 8), 
                    "Low": round(float(val), 8), "Close": round(float(val), 8)
                }
            save_vault(name, vault)
            return True
    except: return False

def run_collector():
    print("=" * 60)
    print(f"📡 [정규 작전] AEGIS 지능형 2-Track 수집기 가동 (실록 연동 모드)")
    print("=" * 60)
    
    fallback_chain = get_fallback_models()
    creds_path = os.getenv("GCP_CREDS_PATH")
    if not creds_path:
        print("❌ GCP_CREDS_PATH 환경 변수를 찾을 수 없습니다.")
        return
        
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path.strip('"').strip("'"), scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    rows = gc.open("AEGIS_Daily_Report").worksheet("XRP 지표").get_all_values()
    success_count = 0
    
    for row in rows[1:]:
        if len(row) < 5: continue
        name, val, src, url, rule = [c.strip() for c in row[:5]]
        if not name: continue
        
        print(f"   ⏳ [{name}] 데이터 분석 및 병합 중...")
        res = False
        
        if src in ['YAHOO', 'UPBIT', 'YAHOO_VOL']: res = fetch_yahoo_upbit_vault(name, url, src)
        elif src == 'FRED': res = fetch_fred_direct(name, url)
        elif src == 'FNG': res = fetch_fng_vault(name, rule)
        elif src in ['JSON_API', 'AI_SCORE', 'MANUAL']: res = process_live_to_vault(name, val, src, url, rule, fallback_chain)
        
        if res: success_count += 1
        print(f"   {'✅' if res else '❌'} [{name}] 처리 완료.")
        
    print(f"\n🎉 작전 종료: 구글 시트에 등록된 {success_count}개 지표가 최신 동향으로 갱신되었습니다.")

if __name__ == "__main__":
    run_collector()