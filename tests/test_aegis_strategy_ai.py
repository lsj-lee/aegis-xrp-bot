import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# --- ENVIRONMENT SHIM ---
def setup_mock_environment():
    mock_modules = [
        "gspread", "google", "google.oauth2", "google.oauth2.service_account",
        "google.genai", "dotenv"
    ]
    for module_name in mock_modules:
        if module_name not in sys.modules:
            mock = MagicMock()
            sys.modules[module_name] = mock

setup_mock_environment()

# --- TARGET IMPORT ---
# We need to import aegis_strategy_ai after mocking
import aegis_strategy_ai

# --- TESTS ---

def test_run_target_prediction_strategy_missing_env():
    """Test that the function handles missing GCP_CREDS_PATH gracefully."""
    # We clear the environment for this test to ensure GCP_CREDS_PATH is missing
    # patch.dict only affects os.environ within the block, but we need to make sure
    # it's clean starting point.

    with patch.dict(os.environ, {}, clear=True), \
         patch('builtins.print') as mock_print:

        aegis_strategy_ai.run_target_prediction_strategy()

        # Verify that it printed the error message
        mock_print.assert_any_call("❌ 인증 파일 누락: GCP_CREDS_PATH 환경변수가 설정되지 않았거나 파일이 존재하지 않습니다.")

def test_run_target_prediction_strategy_missing_file():
    """Test that the function handles missing file at GCP_CREDS_PATH gracefully."""
    with patch.dict(os.environ, {"GCP_CREDS_PATH": "non_existent_file.json"}), \
         patch('os.path.exists', return_value=False), \
         patch('builtins.print') as mock_print:

        aegis_strategy_ai.run_target_prediction_strategy()

        # Verify that it printed the error message
        mock_print.assert_any_call("❌ 인증 파일 누락: GCP_CREDS_PATH 환경변수가 설정되지 않았거나 파일이 존재하지 않습니다.")

def test_run_target_prediction_strategy_success_flow():
    """Test the success flow to ensure we haven't broken the main logic (mocked)."""
    fake_creds_path = "fake_creds.json"

    with patch.dict(os.environ, {"GCP_CREDS_PATH": fake_creds_path, "GEMINI_API_KEY": "fake_key"}), \
         patch('os.path.exists', return_value=True), \
         patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds, \
         patch('gspread.authorize') as mock_authorize, \
         patch('google.genai.Client') as mock_genai_client, \
         patch('builtins.print') as mock_print:

        # Mock gspread interaction
        mock_gc = mock_authorize.return_value
        mock_spreadsheet = mock_gc.open.return_value
        mock_sheet = mock_spreadsheet.worksheet.return_value

        # Mock data return for get_all_values
        # Call 1: Strategy sheet (indices 0, 1)
        # Call 2: Storage sheet (indices 0..2)
        mock_sheet.get_all_values.side_effect = [
            [["Header", "Meaning"], ["Ind1", "Mean1"]], # Strategy sheet
            [["H", "C", "P", "R"], ["XRP", "100", "110", "Reason"], ["BTC", "200", "190", "Reason"]] # Storage sheet
        ]

        # Mock Gemini response
        mock_model = mock_genai_client.return_value.models
        mock_response = MagicMock()
        mock_response.text = "Generated Report Content"
        mock_model.generate_content.return_value = mock_response

        aegis_strategy_ai.run_target_prediction_strategy()

        # Verify success message
        mock_print.assert_any_call("✅ 정밀 리포트 배달 완료.")
