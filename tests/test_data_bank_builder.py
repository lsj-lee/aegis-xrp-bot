import sys
from unittest.mock import MagicMock, patch, ANY
import pytest

# --- ENVIRONMENT SHIM ---
def setup_mock_environment():
    mock_modules = [
        "gspread", "yfinance", "pandas", "numpy", "requests",
        "dotenv", "sklearn", "sklearn.ensemble",
        "google", "google.oauth2", "google.oauth2.service_account"
    ]
    for module_name in mock_modules:
        if module_name not in sys.modules:
            mock = MagicMock()
            sys.modules[module_name] = mock

    if "pandas" in sys.modules:
        mock = sys.modules["pandas"]
        # Ensure MultiIndex is a class, not a Mock object
        class MockMultiIndex:
            def get_level_values(self, level): pass
        mock.MultiIndex = MockMultiIndex
        mock.Timestamp.now.return_value.strftime.return_value = "2026-02-24 12:00"

    if "sklearn.ensemble" in sys.modules:
        mock = sys.modules["sklearn.ensemble"]
        # Ensure it's a class-like mock
        mock.RandomForestRegressor = MagicMock

setup_mock_environment()

# --- TARGET IMPORT ---
from data_bank_builder import AegisM5ResearchCenter

# --- FIXTURES ---

@pytest.fixture
def research_center():
    with patch("google.oauth2.service_account.Credentials.from_service_account_file"), \
         patch("gspread.authorize"):
        return AegisM5ResearchCenter("TestSheet", "fake_key.json")

# --- TESTS ---

def test_clean_df_multiindex(research_center):
    import pandas as pd
    df = MagicMock()
    df.columns = MagicMock(spec=pd.MultiIndex)
    df.columns.get_level_values.return_value = ["Col1", "Col2"]

    cleaned_df = research_center.clean_df(df)

    assert cleaned_df.columns == ["Col1", "Col2"]

def test_clean_df_singleindex(research_center):
    df = MagicMock()
    df.columns = ["Col1", "Col2"]

    cleaned_df = research_center.clean_df(df)
    assert cleaned_df.columns == ["Col1", "Col2"]

def test_get_upbit_price_success(research_center):
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = [{'trade_price': 1000.5}]
        mock_get.return_value = mock_response

        price = research_center.get_upbit_price("KRW-XRP")
        assert price == 1000.5

def test_get_upbit_price_error(research_center):
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Error")
        price = research_center.get_upbit_price("KRW-XRP")
        assert price == "N/A"

def test_run_m5_machine_learning_logic(research_center):
    # Mocking a DataFrame-like object
    class MockDF:
        def __init__(self, prices):
            self.prices = prices
            self.iloc = self
        def __getitem__(self, key):
            return self
        def __setitem__(self, key, value): pass
        def copy(self): return self
        def shift(self, n): return self
        def dropna(self): return self
        def __len__(self): return len(self.prices)
        def __getitem__(self, idx):
            if isinstance(idx, int): return self.prices[idx]
            return self

    # Case 1: Bullish Trend
    df_bullish = MockDF([100.0, 95.0]) # iloc[-1]=95.0
    with patch("data_bank_builder.RandomForestRegressor") as mock_rf_class:
        mock_model = mock_rf_class.return_value
        mock_model.predict.return_value = [110.0]

        pred, reason = research_center.run_m5_machine_learning(df_bullish)

        assert pred == 110.0
        assert "상승 에너지 우세" in reason

    # Case 2: Bearish Trend
    df_bearish = MockDF([100.0, 105.0]) # iloc[-1]=105.0
    with patch("data_bank_builder.RandomForestRegressor") as mock_rf_class:
        mock_model = mock_rf_class.return_value
        mock_model.predict.return_value = [90.0]

        pred, reason = research_center.run_m5_machine_learning(df_bearish)

        assert pred == 90.0
        assert "하락 압력 우세" in reason

def test_run_m5_machine_learning_exception(research_center):
    pred, reason = research_center.run_m5_machine_learning(None)
    assert pred == 0
    assert reason == "분석 불가"

def test_collect_and_relay_flow(research_center):
    import yfinance as yf

    with patch.object(research_center, 'get_upbit_price', side_effect=[1.2, 60000.0]), \
         patch.object(research_center, 'run_m5_machine_learning', side_effect=[(1.3, "Bullish"), (61000.0, "Bullish")]), \
         patch.object(research_center, 'clean_df', return_value=MagicMock()), \
         patch("yfinance.download") as mock_yf_dl:

        mock_spreadsheet = MagicMock()
        mock_sheet = MagicMock()
        research_center.client.open.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_sheet

        research_center.collect_and_relay()

        assert mock_yf_dl.call_count == 2
        mock_sheet.update.assert_called_once()
        call_args = mock_sheet.update.call_args[1]
        values = call_args['values']
        assert values[1][0] == "XRP"
        assert values[1][2] == 1.3

def test_collect_and_relay_sheet_creation(research_center):
    with patch.object(research_center, 'get_upbit_price'), \
         patch.object(research_center, 'run_m5_machine_learning', return_value=(0, "")), \
         patch.object(research_center, 'clean_df'), \
         patch("yfinance.download"):

        mock_spreadsheet = MagicMock()
        research_center.client.open.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.side_effect = Exception("Not found")
        mock_spreadsheet.add_worksheet.return_value = MagicMock()

        research_center.collect_and_relay()

        mock_spreadsheet.add_worksheet.assert_called_with(title="AEGIS_ML_Storage", rows="10", cols="6")
