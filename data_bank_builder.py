import gspread
import os
import json
import yfinance as yf
import pandas as pd
import requests
import time
import subprocess
from google.oauth2.service_account import Credentials
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    import pandas_datareader.data as web
except ImportError:
    web = None

load_dotenv()

DATA_DIR = "aegis_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def check_thermal_safety(limit=80.0):
    try:
        res = subprocess.run(['osx-cpu-temp'], capture_output=True, text=True)
        current_temp = float(res.stdout.strip().replace('°C', ''))
        if current_temp >= limit:
            print(f"   🚨 [비상] M5 코어 온도 {current_temp}°C! 연산 중단.")
            return False
        return True
    except:
        return True 

def load_vault(name):
    path = os.path.join(DATA_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_vault(name, data):
    path = os.path.join(DATA_DIR, f"{name}.json")
    sorted_data = dict(sorted(data.items()))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

def fetch_yahoo_upbit_vault(name, ticker, src_type):
    vault = load_vault(name)
    today_str = datetime.now().strftime("%Y-%m-%d")
    is_insufficient = len(vault) < 500
    precision = 8 if ("BTC" in ticker or "도미넌스" in name) else 4
    
    if not vault or is_insufficient:
        try:
            if src_type == 'YAHOO':
                raw = yf.download(ticker, period="max", progress=False)['Close']
                if not raw.empty: vault = {k.strftime("%Y-%m-%d"): round(float(v), precision) for k, v in raw.squeeze().dropna().to_dict().items()}
            elif src_type == 'UPBIT':
                all_candles, last_to = [], ""
                for _ in range(15):
                    res = requests.get(f"https://api.upbit.com/v1/candles/days?market={ticker}&count=200{last_to}").json()
                    if not res: break
                    all_candles.extend(res)
                    last_to = f"&to={res[-1]['candle_date_time_utc']}"
                    time.sleep(0.1)
                vault = {d['candle_date_time_utc'][:10]: round(float(d['trade_price']), precision) for d in all_candles}
        except Exception: pass
    else:
        last_date = max(vault.keys())
        if last_date < today_str:
            try:
                if src_type == 'YAHOO':
                    raw = yf.download(ticker, start=last_date, progress=False)['Close']
                    if not raw.empty:
                        for k, v in raw.squeeze().dropna().to_dict().items(): vault[k.strftime("%Y-%m-%d")] = round(float(v), precision)
                elif src_type == 'UPBIT':
                    res = requests.get(f"https://api.upbit.com/v1/candles/days?market={ticker}&count=10").json()
                    for d in res: vault[d['candle_date_time_utc'][:10]] = round(float(d['trade_price']), precision)
            except Exception: pass
    if vault: save_vault(name, vault)
    return pd.Series(vault, name=name)

def fetch_fred_vault(name, ticker):
    vault = load_vault(name)
    if web is None: return pd.Series(vault, name=name) if vault else pd.Series(dtype=float)
    try:
        if len(vault) < 500:
            df = web.DataReader(ticker, 'fred', "2010-01-01")
            vault = {k.strftime("%Y-%m-%d"): float(v) for k, v in df[ticker].dropna().to_dict().items()}
        else:
            last_date = max(vault.keys())
            if last_date < datetime.now().strftime("%Y-%m-%d"):
                df = web.DataReader(ticker, 'fred', last_date)
                for k, v in df[ticker].dropna().to_dict().items(): vault[k.strftime("%Y-%m-%d")] = float(v)
        if vault: save_vault(name, vault)
    except Exception: pass
    return pd.Series(vault, name=name)

def fetch_fng_vault(name, rule):
    vault = load_vault(name)
    limit = rule.split('=')[1] if '=' in rule else '2000'
    try:
        if len(vault) < 500:
            res = requests.get(f"https://api.alternative.me/fng/?limit={limit}").json()
            vault = {datetime.fromtimestamp(int(d['timestamp'])).strftime("%Y-%m-%d"): float(d['value']) for d in res['data']}
        else:
            res = requests.get("https://api.alternative.me/fng/?limit=5").json()
            for d in res['data']: vault[datetime.fromtimestamp(int(d['timestamp'])).strftime("%Y-%m-%d")] = float(d['value'])
        if vault: save_vault(name, vault)
    except Exception: pass
    return pd.Series(vault, name=name)

def process_live_to_vault(name, val, src_type, url, rule):
    vault = load_vault(name)
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_val = None
    precision = 8 if "도미넌스" in name else 4
    try:
        if src_type == 'JSON_API' and url:
            res = requests.get(url, timeout=10).json()
            for k in rule.split('.'): res = res[k]
            current_val = round(float(res), precision)
        elif src_type == 'RSS_NEWS' and url:
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10).text.lower()
            current_val = 1.0 if any(k.strip().lower() in res for k in rule.split(',')) else 0.0
        elif src_type == 'MANUAL':
            current_val = float(val) if val else 0.0
        
        if current_val is not None:
            vault[today_str] = current_val
            save_vault(name, vault)
            print(f"   {get_timestamp()} 📝 [볼트 각인] {name}: [{today_str}] 완료.")
    except Exception: pass
    return pd.Series(vault, name=name), current_val

def apply_data_torture(df, target_col):
    df['MA_20'] = df[target_col].rolling(window=20).mean()
    std_20 = df[target_col].rolling(window=20).std()
    df['BB_Upper'] = df['MA_20'] + (std_20 * 2)
    df['BB_Lower'] = df['MA_20'] - (std_20 * 2)
    
    delta = df[target_col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    df['Volatility_14d'] = df[target_col].pct_change().rolling(14).std()

    features_to_lag = [target_col]
    if "비트코인_지수" in df.columns: features_to_lag.append("비트코인_지수")
    
    for col in features_to_lag:
        df[f'{col}_Lag1'] = df[col].shift(1)
        df[f'{col}_Lag3'] = df[col].shift(3)
        df[f'{col}_Lag7'] = df[col].shift(7)
        
    return df.ffill().bfill()

def run_m5_universal_engine():
    now = datetime.now()
    print("=" * 60)
    print(f"🛡️ AEGIS M5 완벽 통합 엔진 가동")
    print(f"📅 작전 실행 일시: {now.strftime('%Y년 %m월 %d일 %H:%M:%S')}")
    print("=" * 60)
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")
    daily_ws = doc.worksheet("AEGIS_Daily_Report")
    settings_ws = doc.worksheet("AEGIS_Settings")
    
    try: daily_ws.update_acell('G1', f"마지막 작전: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    except: pass

    try: n_trees = int(settings_ws.get_all_values()[1][2])
    except: n_trees = 1000

    current_data = daily_ws.get_all_values()
    all_series, updates = [], []

    print(f"\n📡 [1단계] 데이터 정밀 동기화 개시...")
    for idx, row in enumerate(current_data):
        if len(row) <= 6 or not row[4].strip() or row[4].startswith("["): continue
        name, val, src_type, t_url, p_rule = row[4].strip(), row[5].strip(), row[6].upper(), row[8].strip(), row[9].strip()
        
        series, new_f_val = None, None
        if src_type in ['YAHOO', 'UPBIT']: series = fetch_yahoo_upbit_vault(name, t_url, src_type)
        elif src_type == 'FRED': series = fetch_fred_vault(name, t_url)
        elif src_type == 'FNG': series = fetch_fng_vault(name, p_rule)
        elif src_type in ['JSON_API', 'RSS_NEWS', 'MANUAL']: series, _ = process_live_to_vault(name, val, src_type, t_url, p_rule)

        if series is not None and not series.empty:
            all_series.append(series)
            updates.append({'range': f'F{idx+1}', 'values': [[series.iloc[-1]]]})

    if updates: daily_ws.batch_update(updates)

    print("\n🧠 [2단계] M5 뉴럴 엔진 병합 및 학습 개시...")
    df = pd.concat(all_series, axis=1)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index().ffill().bfill()
    
    main_col = "리플_한국" if "리플_한국" in df.columns else (df.columns[0] if len(df.columns) > 0 else None)
    if not main_col: return
    current_price = df[main_col].iloc[-1]

    df = apply_data_torture(df, main_col)

    df['Target_1d'] = df[main_col].shift(-1)
    df['Target_7d'] = df[main_col].shift(-7)
    df['Target_30d'] = df[main_col].shift(-30)

    feature_cols = [col for col in df.columns if not col.startswith('Target')]
    X_today = df[feature_cols].iloc[-1:].values

    def train_and_predict(target_col):
        if not check_thermal_safety(80.0): return 0.0
        
        train_df = df.dropna(subset=[target_col])
        if train_df.empty: return 0.0
        X_train, y_train = train_df[feature_cols].values, train_df[target_col].values
        
        model = RandomForestRegressor(n_estimators=n_trees, n_jobs=-1, random_state=42)
        model.fit(X_train, y_train)
        return round(model.predict(X_today)[0], 4)

    print(f"   {get_timestamp()} ⚡ [연산] {len(feature_cols)}개 변수 M5 병렬 처리 중... (트리: {n_trees})")
    
    t_start = time.time()
    p_1d = train_and_predict('Target_1d')
    p_7d = train_and_predict('Target_7d')
    p_30d = train_and_predict('Target_30d')
    t_end = time.time()
    
    if p_30d == 0.0: return

    latest_rsi = round(df['RSI_14'].iloc[-1], 2)
    latest_bb_lower = round(df['BB_Lower'].iloc[-1], 2)
    latest_bb_upper = round(df['BB_Upper'].iloc[-1], 2)

    history_sheet = doc.worksheet("AEGIS_History")
    history_sheet.append_row([
        now.strftime("%Y-%m-%d %H:%M:%S"), 
        f"{current_price:.4f}", 
        f"{p_1d}", f"{p_7d}", f"{p_30d}", 
        f"RSI: {latest_rsi}, BB하단: {latest_bb_lower}, BB상단: {latest_bb_upper}"
    ])
    
    print(f"   ✅ [연산 완료] 소요 시간: {t_end - t_start:.2f}초")
    print("=" * 60)

if __name__ == "__main__":
    run_m5_universal_engine()