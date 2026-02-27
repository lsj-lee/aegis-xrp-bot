import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

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
import aegis_strategy_ai

def test_optimization_no_redundant_api_call():
    """
    Performance Regression Test:
    Ensures that when '[시트 기록용]' is present in the report, the code does NOT call
    strategy_worksheet.col_values(1) to check for existence, but instead uses the
    already loaded data from get_all_values().
    """
    fake_creds_path = "fake_creds.json"

    # We patch 'aegis_strategy_ai.genai.Client' to be absolutely sure we hit the right reference
    with patch.dict(os.environ, {"GCP_CREDS_PATH": fake_creds_path, "GEMINI_API_KEY": "fake_key"}), \
         patch('os.path.exists', return_value=True), \
         patch('google.oauth2.service_account.Credentials.from_service_account_file'), \
         patch('gspread.authorize') as mock_authorize, \
         patch('aegis_strategy_ai.genai.Client') as mock_genai_client:

        # Mock gspread interaction
        mock_gc = mock_authorize.return_value
        mock_spreadsheet = mock_gc.open.return_value

        # We need to distinguish between worksheets
        mock_strategy_sheet = MagicMock(name="StrategySheet")
        mock_storage_sheet = MagicMock(name="StorageSheet")
        mock_results_sheet = MagicMock(name="ResultsSheet")

        def worksheet_side_effect(name):
            if name == "AEGIS_Daily_Report":
                return mock_strategy_sheet
            elif name == "AEGIS_ML_Storage":
                return mock_storage_sheet
            elif name == "AEGIS_Daily_Report Results":
                return mock_results_sheet
            return MagicMock(name=f"UnknownSheet_{name}")

        mock_spreadsheet.worksheet.side_effect = worksheet_side_effect
        mock_spreadsheet.add_worksheet.return_value = mock_results_sheet

        # Mock data return for get_all_values
        existing_tag = "EXISTING_TAG"
        mock_data = [
            ["Tag", "Suggestion"],
            [existing_tag, "Old Suggestion"]
        ]
        mock_strategy_sheet.get_all_values.return_value = mock_data

        mock_storage_sheet.get_all_values.return_value = [
            ["H", "C", "P", "R"],
            ["XRP", "100", "110", "Reason"],
            ["BTC", "200", "190", "Reason"]
        ]

        # Mock Gemini response
        mock_model = mock_genai_client.return_value.models
        mock_response = MagicMock(name="GeminiResponse")
        mock_response.text = "Report Content...\n[시트 기록용]\nNew Suggestion"

        # Ensure generate_content returns our mock_response
        mock_model.generate_content.return_value = mock_response

        # Execute
        print("\n--- START EXECUTION ---")
        aegis_strategy_ai.run_target_prediction_strategy()
        print("--- END EXECUTION ---")

        # --- VERIFICATION ---

        # 1. Verify col_values(1) was NOT called
        mock_strategy_sheet.col_values.assert_not_called()

        # 2. Verify append_row WAS called
        try:
            mock_strategy_sheet.append_row.assert_called_once()
        except AssertionError as e:
            print("\nDEBUG: Strategy Sheet Calls:", mock_strategy_sheet.mock_calls)
            raise e

        # 3. Verify get_all_values was called (baseline)
        mock_strategy_sheet.get_all_values.assert_called_once()

def test_optimization_avoid_duplicate_append():
    """
    Ensures that if the tag IS found in the pre-loaded data, append_row is NOT called.
    """
    fake_creds_path = "fake_creds.json"

    with patch.dict(os.environ, {"GCP_CREDS_PATH": fake_creds_path, "GEMINI_API_KEY": "fake_key"}), \
         patch('os.path.exists', return_value=True), \
         patch('google.oauth2.service_account.Credentials.from_service_account_file'), \
         patch('gspread.authorize') as mock_authorize, \
         patch('aegis_strategy_ai.genai.Client') as mock_genai_client:

        mock_gc = mock_authorize.return_value
        mock_spreadsheet = mock_gc.open.return_value
        mock_strategy_sheet = MagicMock(name="StrategySheet")
        mock_storage_sheet = MagicMock(name="StorageSheet")
        mock_results_sheet = MagicMock(name="ResultsSheet")

        def worksheet_side_effect(name):
            if name == "AEGIS_Daily_Report":
                return mock_strategy_sheet
            elif name == "AEGIS_ML_Storage":
                return mock_storage_sheet
            elif name == "AEGIS_Daily_Report Results":
                return mock_results_sheet
            return MagicMock()

        mock_spreadsheet.worksheet.side_effect = worksheet_side_effect

        # Calculate what the tag will be for today
        today_tag = f"AI_자율기록_{datetime.now().strftime('%m%d')}"

        # Mock data: The tag ALREADY EXISTS in the loaded data
        mock_strategy_sheet.get_all_values.return_value = [
            ["Tag", "Suggestion"],
            [today_tag, "Already Existing Suggestion"]
        ]

        mock_storage_sheet.get_all_values.return_value = [
            ["H", "C", "P", "R"], ["XRP", "100", "110", "Reason"], ["BTC", "200", "190", "Reason"]
        ]

        mock_model = mock_genai_client.return_value.models
        mock_response = MagicMock(name="GeminiResponse")
        mock_response.text = "Report...\n[시트 기록용]\nDuplicate Suggestion"
        mock_model.generate_content.return_value = mock_response

        # Execute
        aegis_strategy_ai.run_target_prediction_strategy()

        # --- VERIFICATION ---

        # 1. Verify col_values(1) was NOT called
        mock_strategy_sheet.col_values.assert_not_called()

        # 2. Verify append_row was NOT called because tag exists in loaded data
        mock_strategy_sheet.append_row.assert_not_called()
