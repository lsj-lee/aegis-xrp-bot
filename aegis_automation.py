import os
import datetime
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
import warnings
warnings.filterwarnings('ignore')

from aegis_executor import run_daily_execution

def parse_gemini_report(full_report):
    """
    Parses the full report string to extract specific sections using Regex and string searching.
    Returns a dictionary with keys: target, chain, evolution, action, decision.
    """
    sections = {
        'target': '',
        'chain': '',
        'evolution': '',
        'action': '',
        'decision': '분석 완료'
    }

    try:
        # 1. Locate Key Sections
        # We look for the Gemini headers. Note: Gemini usually adds a colon like "[🎯 타점 분석]:"
        # However, to be safe, we regex for the bracketed part and optional colon.

        # We need the positions of these headers
        target_match = re.search(r"\[🎯 타점 분석\]:?", full_report)
        chain_match = re.search(r"\[🧠 AEGIS 사고의 사슬\]:?", full_report)
        evol_match = re.search(r"\[🧬 에이지스 진화 연구\]:?", full_report)
        code_match = re.search(r"\[💻 진화 코드 제안\]:?", full_report)
        action_match = re.search(r"\[🔥 최종 액션 플랜\]:?", full_report)

        # Helper to get content between two indices
        def get_text(start_match, end_match):
            if start_match and end_match:
                return full_report[start_match.start():end_match.start()].strip()
            elif start_match:
                return full_report[start_match.start():].strip()
            return ""

        # [Target Analysis]
        # Includes the pre-Gemini "Code Analysis" block + Gemini's Target Analysis
        if target_match:
            # Code Analysis is everything before the first Gemini Target header
            # Wait, `run_daily_execution` puts `code_analysis` first.
            # `code_analysis` starts with `[🎯 타점 분석] & ...`.
            # Gemini starts with `[🎯 타점 분석]:` (colon).
            # If we find the COLON version, we assume it's Gemini.

            gemini_start_idx = target_match.start()

            # If the match is actually the Code Analysis header (no colon, or colon absent in regex?),
            # we need to be careful. Code Analysis header: `[🎯 타점 분석] & [🤖 DNN & 선물 지표]`
            # Gemini header: `[🎯 타점 분석]:`

            # Let's search specifically for the Gemini one with Colon first
            gemini_target_match = re.search(r"\[🎯 타점 분석\]:", full_report)

            if gemini_target_match:
                # Code Analysis is before this
                code_analysis = full_report[:gemini_target_match.start()].strip()
                # Gemini Target is from here to Chain
                gemini_target = get_text(gemini_target_match, chain_match)

                sections['target'] = f"{code_analysis}\n\n{gemini_target}"
            else:
                # Fallback: Treat everything up to Chain as Target
                sections['target'] = get_text(target_match, chain_match)
        else:
             sections['target'] = full_report # Worst case

        # [Chain of Thought]
        sections['chain'] = get_text(chain_match, evol_match)

        # [Evolution Research]
        # Excludes Code Proposal if present
        if code_match:
            sections['evolution'] = get_text(evol_match, code_match)
        else:
            sections['evolution'] = get_text(evol_match, action_match)

        # [Action Plan]
        sections['action'] = get_text(action_match, None) # To end

        # [Decision Extraction]
        # Look for 강세/약세/중립 in Action Plan
        if sections['action']:
            if "강세" in sections['action']:
                sections['decision'] = "강세"
            elif "약세" in sections['action']:
                sections['decision'] = "약세"
            elif "중립" in sections['action']:
                sections['decision'] = "중립"

    except Exception as e:
        print(f"⚠️ 리포트 파싱 중 오류: {e}")
        sections['target'] = full_report

    return sections

def update_google_sheet(report_data):
    print("📊 구글 시트에 AI 상세 리포트를 전송합니다...")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = "/Users/lsj/Desktop/구글 연결 키/creds xrp coin.json"
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        
        sheet_name = "AEGIS_Daily_Report" 
        sheet = client.open(sheet_name).sheet1
        
        # Parse the commentary
        parsed = parse_gemini_report(report_data['commentary'])

        # Override decision if extracted from Gemini
        decision = parsed['decision'] if parsed['decision'] != '분석 완료' else report_data['decision']

        # Prepare Row Data
        # [날짜, 현재가, 공포지수, 예측확률, 판단, 추세, 타점분석, 사고의사슬, 진화리포트, 최종액션플랜]
        row_data = [
            report_data['date'],
            report_data['price'],
            report_data['fng'],
            f"{report_data['prob']:.2f}%",
            decision,
            report_data['long_term'],
            parsed['target'],     # 타점분석 (Code + Gemini)
            parsed['chain'],      # 사고의사슬
            parsed['evolution'],  # 진화리포트
            parsed['action']      # 최종액션플랜
        ]
        
        # Check if sheet is empty (read first row)
        existing_data = sheet.get_all_values()
        if not existing_data:
            header = ['날짜', '현재가', '공포지수', '예측확률', '판단', '추세', '타점분석', '사고의사슬', '진화리포트', '최종액션플랜']
            sheet.append_row(header)
            print("✅ 시트가 비어있어 헤더를 생성했습니다.")

        sheet.append_row(row_data)
        print(f"✅ 구글 시트('{sheet_name}') 업데이트 완료!")
        
    except Exception as e:
        print(f"⚠️ 시트 업데이트 오류 발생: {e}")

def run_automated_pipeline():
    print(f"⏰ [AEGIS 3.0 자동화 파이프라인 가동] - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = run_daily_execution()
    if result:
        print("\n" + result['commentary'])
        update_google_sheet(result)

if __name__ == "__main__":
    run_automated_pipeline()
