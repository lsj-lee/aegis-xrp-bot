import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [본부] AEGIS 6.0 자율 진화 및 분산 지능 엔진 가동...")
    
    # 1. 구글 시트 인증 및 접속
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_path = "creds xrp coin.json"
    
    if not os.path.exists(creds_path):
        print(f"❌ 오류: 인증 파일({creds_path})을 찾을 수 없습니다.")
        return

    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    
    try:
        spreadsheet = gc.open("AEGIS_Daily_Report")
        strategy_worksheet = spreadsheet.worksheet("AEGIS_Daily_Report")
        
        # 사령관 전략 지표 로드 (AI가 내일 읽을 데이터)
        rows = strategy_worksheet.get_all_values()[1:]
        payload = [{"지표": r[0], "분석의미": r[1] if len(r)>1 else ""} for r in rows if r[0]]
    except Exception as e:
        print(f"❌ 시트 로드 실패: {e}")
        return

    # 2. 맥북 M5가 남긴 ML 데이터 읽기 (AEGIS_ML_Storage 탭)
    try:
        storage_sheet = spreadsheet.worksheet("AEGIS_ML_Storage")
        ml_values = storage_sheet.get_all_values()
        # ml_values[1] -> XRP, ml_values[2] -> BTC
        ml_context = {
            "XRP": {"현재가": ml_values[1][1], "ML예측": ml_values[1][2], "ML근거": ml_values[1][3]},
            "BTC": {"현재가": ml_values[2][1], "ML예측": ml_values[2][2], "ML근거": ml_values[2][3]},
            "연산시간": ml_values[1][4]
        }
    except Exception as e:
        print(f"⚠️ ML 데이터를 찾을 수 없습니다. 일반 분석 모드로 전환합니다.")
        ml_context = "데이터 부재"

    # 3. 제미나이 2.5 플래시 - 자율 진화 프롬프트 설정
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""
    [지휘 지침: AEGIS 자율 진화 및 타점 분석]
    너는 맥북 M5 연구소의 수학적 데이터와 사령관의 전략 지표를 융합하는 수석 전략가이다.

    [핵심 입력 데이터]
    - 맥북 M5 ML 연산 및 근거: {json.dumps(ml_context, ensure_ascii=False)}
    - 현재 사령관 전략 지표: {json.dumps(payload, ensure_ascii=False)}

    [출력 필수 항목]
    1. 현재 가격 최저점 판별 (확률 % 및 근거 요약)
    2. 단기 타점: M5의 예측가와 근거를 반영한 업비트 원화 가격 + 추측 이유
    3. 중기 타점: 3월 1일 정책 등 거시 지표 반영 + 업비트 원화 가격 + 추측 이유
    4. 장기 타점: 2026 대불장 사이클 반영 + 업비트 원화 가격 + 추측 이유
    5. [AI 자율 제안]: 시스템 고도화를 위해 사령관에게 제안하는 새로운 지표나 분석 방향

    [특수 임무: 자가 기록]
    시장 상황에서 내일 분석에 반드시 반영해야 할 핵심 키워드가 있다면, 아래 형식을 본문 마지막에 정확히 기입하라.
    형식: [시트 기록용] 내용
    (예: [시트 기록용] 미국 금리 동결 가능성에 따른 알트코인 수급 변화 주시 필요)

    * 모든 가격에 (업비트 기준 약 0,000원) 병기.
    * 타점 끝에 (추측입니다) 명시.
    """

    try:
        print("📡 Gemini 본부와 교신 중... 전략 리포트 생성 중")
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        # 🚀 4. [진화 로직] 제미나이의 자율 기록을 전략 지표 탭에 추가
        if "[시트 기록용]" in report:
            try:
                # [시트 기록용] 뒤의 문구만 추출
                suggestion = report.split("[시트 기록용]")[1].split("\n")[0].strip()
                tag = f"AI_자율기록_{datetime.now().strftime('%m%d')}"
                
                # 중복 기록 방지 (이미 같은 태그가 있는지 확인)
                existing_tags = strategy_worksheet.col_values(1)
                if tag not in existing_tags:
                    strategy_worksheet.append_row([tag, suggestion])
                    print(f"🧬 AI 자율 진화: 전략 지표에 '{suggestion}'을(를) 기록했습니다.")
            except Exception as se:
                print(f"⚠️ 자율 기록 실패: {se}")

        # 5. 최종 리포트 결과 탭에 기록
        try:
            results_worksheet = spreadsheet.worksheet("AEGIS_Daily_Report Results")
        except:
            results_worksheet = spreadsheet.add_worksheet(title="AEGIS_Daily_Report Results", rows="100", cols="10")
        
        results_worksheet.clear()
        paragraphs = [p.strip() for p in report.split('\n\n') if p.strip()]
        header = [[f"🛡️ AEGIS 분산 지능 및 자율 진화 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"], ["="*60]]
        final_values = header + [[p] for p in paragraphs]
        
        try:
            results_worksheet.update(values=final_values, range_name="A1")
        except:
            results_worksheet.update("A1", final_values)

        print("✅ 작전 성공: 자율 진화 리포트가 구글 시트에 배달되었습니다.")

    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()