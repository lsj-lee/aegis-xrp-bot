import os
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime

# 💾 파일 제목: aegis_ml_engine.py
# 🚀 사유: 3단계 동기화(syncer)를 위한 timestamp 및 raw_latest 데이터 산출 로직 추가

def run_ml_engine():
    print("=" * 60)
    print("🧠 [2단계] AEGIS M5 연산 및 학습 분과 가동 (OHLC 꼬리 분석 탑재)")
    print("=" * 60)
    
    RAW_DIR = os.path.join("aegis_data", "raw")
    RESULTS_DIR = os.path.join("aegis_data", "results")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    data_frames = []
    files = [f for f in os.listdir(RAW_DIR) if f.endswith('.json')]
    
    raw_latest = {} # 🎯 시트 동기화를 위한 최신값 저장소

    print("📡 로컬 볼트(Vault) 입체 데이터 장전 중...")
    for f in files:
        name = f.replace('.json', '')
        with open(os.path.join(RAW_DIR, f), 'r', encoding='utf-8') as file:
            vault = json.load(file)

        if not vault: continue

        # 🚀 3단계 Syncer를 위해 각 지표의 '가장 최근 Close 값'을 추출
        latest_date = sorted(vault.keys())[-1]
        latest_entry = vault[latest_date]
        if isinstance(latest_entry, dict):
            raw_latest[name] = float(latest_entry.get("Close", 0.0))
        else:
            raw_latest[name] = float(latest_entry)

        # OHLC 딕셔너리인지 단순 숫자인지 판별하여 데이터프레임 확장
        sample_val = next(iter(vault.values()))
        if isinstance(sample_val, dict):
            df = pd.DataFrame.from_dict(vault, orient='index')
            df.columns = [f"{name}_{col}" for col in df.columns] # 예: 리플_한국_High
        else:
            df = pd.DataFrame.from_dict(vault, orient='index', columns=[name])

        df.index = pd.to_datetime(df.index)
        data_frames.append(df)

    if not data_frames:
        print("❌ 데이터가 없습니다.")
        return

    # Pandas 병합 경고(Warning) 제거를 위해 sort=False 명시
    master_df = pd.concat(data_frames, axis=1, sort=False).sort_index().ffill().dropna()

    # 타겟 설정 (Close 가격 기준)
    target_col = '리플_한국_Close' if '리플_한국_Close' in master_df.columns else '리플_한국'
    if target_col not in master_df.columns:
        print("❌ 타겟 데이터(리플_한국)가 부족합니다.")
        return

    current_price = float(master_df[target_col].iloc[-1])

    # 🚀 전투력 측정 (Feature Engineering): 꼬리 길이와 변동성 계산
    if '리플_한국_High' in master_df.columns and '리플_한국_Low' in master_df.columns:
        master_df['XRP_Volatility'] = master_df['리플_한국_High'] - master_df['리플_한국_Low']
        master_df['XRP_Wick_Upper'] = master_df['리플_한국_High'] - master_df[['리플_한국_Open', '리플_한국_Close']].max(axis=1)
        master_df['XRP_Wick_Lower'] = master_df[['리플_한국_Open', '리플_한국_Close']].min(axis=1) - master_df['리플_한국_Low']

    print(f"   [연산] ⚡ {len(master_df.columns)}개 다차원 변수 M5 병렬 처리 중... (트리: 1000)")
    import time
    start_t = time.time()

    predictions = {}
    for days in [1, 7, 30]:
        y = master_df[target_col].shift(-days)
        X = master_df.copy()

        valid_idx = y.dropna().index
        X_train = X.loc[valid_idx]
        y_train = y.loc[valid_idx]
        X_latest = X.iloc[-1:]

        if len(X_train) < 50:
            predictions[f'predict_{days}d'] = 0.0
            continue

        model = RandomForestRegressor(n_estimators=1000, n_jobs=-1, random_state=42)
        model.fit(X_train, y_train)
        pred = model.predict(X_latest)[0]
        predictions[f'predict_{days}d'] = round(float(pred), 4)

    # 🎯 3단계(Syncer)가 요구하는 필수 데이터 규격 완성
    result_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_price": current_price,
        "predict_1d": predictions.get('predict_1d', 0),
        "predict_7d": predictions.get('predict_7d', 0),
        "predict_30d": predictions.get('predict_30d', 0),
        "indicators": len(master_df.columns),
        "raw_latest": raw_latest
    }

    today_str = datetime.now().strftime("%Y%m%d")
    result_path = os.path.join(RESULTS_DIR, f"result_{today_str}.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ [연산 완료] 소요 시간: {round(time.time() - start_t, 2)}초")
    print(f"   💾 [결과 저장] {result_path}")

if __name__ == "__main__":
    run_ml_engine()