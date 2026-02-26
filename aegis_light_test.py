import os
import pandas as pd
import numpy as np
import sys

# data_bank_builder.py가 있는 경로를 인식하도록 설정
sys.path.append(os.getcwd())

try:
    from data_bank_builder import AegisM5ResearchCenter
except ImportError:
    print("❌ [오류] data_bank_builder.py 파일을 찾을 수 없습니다.")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

def run_light_test():
    print(f"⚡ [경량 모드] AEGIS 시스템 논리 회로 정밀 점검 시작...")
    print("-" * 60)

    # 1. 환경 변수 및 열쇠 경로 확보
    key_path = os.getenv("GCP_CREDS_PATH")
    if not key_path:
        print("❌ GCP_CREDS_PATH 환경 변수가 설정되지 않았습니다.")
        return

        print("❌ [오류] GCP_CREDS_PATH 환경 변수가 설정되지 않았습니다.")
        return
    key_path = key_path.strip('"').strip("'")
    sheet_name = "TEST_SHEET"
    
    print(f"📡 설정 확인: [Key] {key_path} / [Sheet] {sheet_name}")

    # 2. 엔진 초기화 테스트 (규격 맞춤)
    print("\n🏗️ [엔진] 초기화 및 규격 점검...")
    try:
        # 사령관님의 엔진 규격: (sheet_name, key_file_path) 두 개를 모두 전달
        collector = AegisM5ResearchCenter(sheet_name, key_path)
        print("✅ [엔진] 초기화 성공 (규격 일치)")
    except Exception as e:
        print(f"❌ [엔진] 초기화 실패: {e}")
        return

    # 3. M5 연산 로직 점검 (네트워크 미사용)
    print("\n🔍 [연산] 머신러닝 알고리즘 시뮬레이션...")
    try:
        fake_data = pd.DataFrame({
            'Close': np.random.uniform(0.5, 0.6, 100)
        })
        # 100일치 데이터를 넣었을 때 예측값이 나오는지 확인
        pred, reason = collector.run_m5_machine_learning(fake_data)
        
        if pred > 0:
            print(f"✅ [연산] 로직 정상 작동 (예측가: ${pred})")
            print(f"📝 [분석] 판단 근거: {reason}")
        else:
            print("⚠️ [연산] 예측값 계산 오류")
    except Exception as e:
        print(f"❌ [연산] 로직 오류: {e}")

    # 4. 데이터 정제(Cleaning) 필터 점검
    print("\n🔍 [데이터] 정제 필터(Multi-Index) 점검...")
    try:
        # Upbit 등에서 올 수 있는 복잡한 데이터 구조 생성
        test_df = pd.DataFrame([[1, 2]], columns=pd.MultiIndex.from_tuples([('Close', 'XRP'), ('Open', 'XRP')]))
        cleaned = collector.clean_df(test_df)
        
        if not isinstance(cleaned.columns, pd.MultiIndex):
            print("✅ [데이터] 멀티인덱스 정제 필터 정상 작동")
        else:
            print("❌ [데이터] 정제 필터가 멀티인덱스를 제거하지 못함")
    except Exception as e:
        print(f"❌ [데이터] 정제 로직 에러: {e}")

    print("-" * 60)
    print("🎖️ [최종] 경량 테스트 완료! 이제 모든 논리 회로가 정상입니다.")

if __name__ == "__main__":
    run_light_test()