# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime
from google import genai
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

class AegisSniperArmory:
    """
    🎯 [자율 무기고 - AEGIS M5 에디션] 
    등급별로 최신 무기부터 우선 검수하며, 10초 대기 및 사격 테스트를 통해 
    '진짜 사용 가능한 무기' 3개를 확보하여 AEGIS_Settings 탭에 동기화합니다.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(self.base_dir, '.env'))
        
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("❌ [오류] 환경 변수에 GEMINI_API_KEY가 없습니다.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.weapons = {"고급": [], "중급": [], "하급": []}
        
    def _execute_full_scout_and_verify(self):
        print("\n📡 [1단계] 구글 무기 창고 전수 조사 및 최신순 정렬 중...")
        try:
            all_models = list(self.client.models.list())
            print(f"   ✅ 총 {len(all_models)}개의 모델 후보 발견.")

            scanned_categories = {"고급": [], "중급": [], "하급": []}
            for m in all_models:
                m_id = m.name
                if "pro" in m_id.lower() and "vision" not in m_id.lower():
                    scanned_categories["고급"].append(m_id)
                elif "flash" in m_id.lower() and "lite" not in m_id.lower() and "8b" not in m_id.lower():
                    scanned_categories["중급"].append(m_id)
                elif any(x in m_id.lower() for x in ["lite", "8b", "nano"]):
                    scanned_categories["하급"].append(m_id)

            print("\n📊 [2단계] 등급별 최대 3개 확보 작전 (10초 냉각 적용)...")
            
            for tier in ["고급", "중급", "하급"]:
                candidates = scanned_categories[tier]
                candidates.sort(reverse=True) # 최신 버전이 위로 오도록 정렬
                
                if not candidates: continue
                
                print(f"\n  [{tier} 무기군 검수 중...]")
                success_count = 0 
                
                for model_id in candidates:
                    print(f"   - {model_id} 격발 테스트... (⏳ 10초 대기)")
                    time.sleep(10) # 429 Quota 에러 방지용 필수 냉각 시간
                    
                    try:
                        # 💡 실제 API를 찔러서 에러가 나는지 물리적 검증
                        response = self.client.models.generate_content(model=model_id, contents="1")
                        if response.text:
                            self.weapons[tier].append(model_id)
                            success_count += 1
                            print(f"   ✅ [장전 완료]: {model_id} (현재 {success_count}개 확보)")
                            
                            if success_count >= 3:
                                print(f"   🎯 {tier} 등급 최대 확보량(3개) 도달. 다음 등급으로 이동합니다.")
                                break 
                                
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "quota" in error_str.lower():
                            print(f"   ⚠️ [잔탄 없음/할당량 초과]: {model_id}")
                        else:
                            print(f"   ❌ [불발]: {model_id}")
                            
            return True
        except Exception as e:
            print(f"❌ 전수 조사 중 치명적 오류: {e}")
            return False

    def _update_control_panel(self):
        print("\n📈 [3단계] 검증된 무기를 구글 시트 컨트롤 패널에 동기화합니다...")
        try:
            # 기존 AEGIS 환경에 맞춘 인증 및 시트 연결
            creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            gc = gspread.authorize(creds)
            
            spreadsheet = gc.open("AEGIS_Daily_Report")
            try:
                config_ws = spreadsheet.worksheet("AEGIS_Settings")
            except:
                config_ws = spreadsheet.add_worksheet(title="AEGIS_Settings", rows="10", cols="6")
            
            # "models/" 접두사 제거
            def clean_models(model_list):
                return [m.replace("models/", "") for m in model_list]
            
            # 확보된 무기가 3개가 안 될 경우 빈칸으로 채움
            pro_models = clean_models(self.weapons["고급"]) + [""] * 3
            mid_models = clean_models(self.weapons["중급"]) + [""] * 3
            low_models = clean_models(self.weapons["하급"]) + [""] * 3

            # 💡 기존 코드(data_bank_builder 등) 호환성을 위해 C열에 ML 트리 개수 배치
            header = ["무기_등급", "1순위_AI_모델", "ML_트리개수", "2순위_AI_후보", "3순위_AI_후보"]
            row_pro = ["🔥 고급 (High)", pro_models[0], "500", pro_models[1], pro_models[2]]
            row_mid = ["⚙️ 중급 (Mid)", mid_models[0], "100", mid_models[1], mid_models[2]]
            row_low = ["🔫 하급 (Low)", low_models[0], "10", low_models[1], low_models[2]]

            config_ws.clear()
            config_ws.update(range_name="A1", values=[header, row_pro, row_mid, row_low])
            
            print(f"   ✅ 무기 리스트 시트 자동 세팅 완료! (기존 코드 완벽 호환 보장)")
        except Exception as e:
            print(f"   ❌ 대시보드 시트 기록 실패: {e}")

    def run_scan_and_report(self):
        if self._execute_full_scout_and_verify():
            self._update_control_panel()
            return True
        return False

def scan_and_report():
    try:
        armory = AegisSniperArmory()
        return armory.run_scan_and_report()
    except Exception as e:
        print(f"❌ [시스템 오류]: {e}")
        return False

if __name__ == "__main__":
    scan_and_report()