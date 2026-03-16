import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
RESULTS_DIR = os.path.join("aegis_data", "results")

def get_weapon_chain(gc):
    try:
        ws = gc.open("AEGIS_Daily_Report").worksheet("AEGIS_Settings")
        rows = ws.get_all_values()
        chain = []
        for row in rows[1:4]:
            if len(row) > 1 and row[1].strip(): chain.append(row[1].strip())
            if len(row) > 3 and row[3].strip(): chain.append(row[3].strip())
            if len(row) > 4 and row[4].strip(): chain.append(row[4].strip())
        return chain if chain else ["gemini-2.5-pro", "gemini-2.5-flash"]
    except: return ["gemini-2.5-pro", "gemini-2.5-flash"]

def run_final_synthesis():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"👑 [수석 전략관] XRP 3원화 관점 전략 종합 및 시트 타격 가동... ({now_str})")
    
    try:
        with open(os.path.join(RESULTS_DIR, "insight_report.txt"), "r", encoding="utf-8") as f: insight_text = f.read()
        with open(os.path.join(RESULTS_DIR, "logic_report.txt"), "r", encoding="utf-8") as f: logic_text = f.read()
    except Exception as e:
        print(f"❌ 참모 보고서 누락 ({e})")
        return

    files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("result_") and f.endswith(".json")]
    if not files: return
    with open(os.path.join(RESULTS_DIR, max(files)), "r", encoding="utf-8") as f: m5_data = json.load(f)

    m5_predictions = f"- 현재가: {m5_data.get('current_price')}\n- 1일: {m5_data.get('predict_1d')}\n- 7일: {m5_data.get('predict_7d')}\n- 30일: {m5_data.get('predict_30d')}"

    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
    당신은 수석 전략관입니다. 아래 데이터를 바탕으로 XRP 방향성을 단기/중기/장기로 나누어 '하락가 OOO원 / 상승가 OOO원'을 명시하십시오.
    [데이터 1: M5] {m5_predictions}
    [데이터 2: 통찰] {insight_text}
    [데이터 3: 논리] {logic_text}
    
    출력 형식:
    SEC_1 \n ■ [M5 머신러닝 관점] ...
    SEC_2 \n ■ [어슴새벽(제2참모) 관점] ...
    SEC_3 \n ■ [M5 + 제미나이 융합 관점] ...
    SEC_4 \n ■ [수석 전략관 종합 결과] ...
    """

    weapons = get_weapon_chain(gc)
    report = ""
    for model_name in weapons:
        print(f"   🔫 [{model_name}] 무기 장착. 사격 시도...")
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=types.GenerateContentConfig(temperature=0.3))
            report = response.text
            print(f"   ✅ [{model_name}] 사격 명중!")
            break
        except Exception as e:
            print(f"   ⚠️ [총기 잼 발생] {model_name} 실패. 즉시 다음 무기로 교체합니다.")
            time.sleep(1)

    if not report: return

    sections = {}
    for i in range(1, 5):
        start_marker = f"SEC_{i}"
        end_marker = f"SEC_{i+1}" if i < 4 else None
        s_idx = report.find(start_marker)
        if s_idx != -1:
            sections[f"SEC_{i}"] = report[s_idx+len(start_marker):report.find(end_marker) if end_marker else len(report)].strip()

    print(f"   🔗 구글 시트 전송 중...")
    results_ws = gc.open("AEGIS_Daily_Report").worksheet("AEGIS_Daily_Report Results")
    results_ws.clear()
    
    final_sheet_data = [[f"🛡️ AEGIS 수석 전략 3원화 입체 보고서 ({now_str})"], [""]]
    for i in range(1, 5):
        if sections.get(f"SEC_{i}"):
            for line in sections[f"SEC_{i}"].split('\n'):
                final_sheet_data.append([line.strip()])
            final_sheet_data.append([""])

    results_ws.update(range_name="A1", values=final_sheet_data)
    print("   ✅ [AEGIS_Daily_Report Results] 탭 타격 성공.")

if __name__ == "__main__":
    run_final_synthesis()