import sys
from unittest.mock import MagicMock, patch
import unittest

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
        class MockMultiIndex:
            def get_level_values(self, level): pass
        mock.MultiIndex = MockMultiIndex
        mock.Timestamp.now.return_value.strftime.return_value = "2026-02-24 12:00"

    if "sklearn.ensemble" in sys.modules:
        mock = sys.modules["sklearn.ensemble"]
        mock.RandomForestRegressor = MagicMock

setup_mock_environment()

# --- NOW IMPORT ---
from data_bank_builder import AegisM5ResearchCenter

class TestDataBankInputValidation(unittest.TestCase):
    def setUp(self):
        self.patcher_creds = patch("google.oauth2.service_account.Credentials.from_service_account_file")
        self.patcher_auth = patch("gspread.authorize")
        self.patcher_isfile = patch("os.path.isfile", return_value=True)

        self.mock_creds = self.patcher_creds.start()
        self.mock_auth = self.patcher_auth.start()
        self.mock_isfile = self.patcher_isfile.start()

        self.research_center = AegisM5ResearchCenter("TestSheet", "fake_key.json")

    def tearDown(self):
        self.patcher_creds.stop()
        self.patcher_auth.stop()
        self.patcher_isfile.stop()

    @patch("data_bank_builder.requests.get")
    def test_get_upbit_price_none_input(self, mock_get):
        """Test that None input returns 'N/A' and does not crash."""
        print("\nTesting None input...")
        result = self.research_center.get_upbit_price(None)
        self.assertEqual(result, "N/A")
        mock_get.assert_not_called()
        print("SUCCESS: None input handled correctly.")

    @patch("data_bank_builder.requests.get")
    def test_get_upbit_price_int_input(self, mock_get):
        """Test that integer input returns 'N/A' and does not crash."""
        print("\nTesting Integer input...")
        result = self.research_center.get_upbit_price(12345)
        self.assertEqual(result, "N/A")
        mock_get.assert_not_called()
        print("SUCCESS: Integer input handled correctly.")

    @patch("data_bank_builder.requests.get")
    def test_get_upbit_price_empty_string(self, mock_get):
        """Test that empty string returns 'N/A'."""
        print("\nTesting Empty String...")
        result = self.research_center.get_upbit_price("")
        self.assertEqual(result, "N/A")
        mock_get.assert_not_called()
        print("SUCCESS: Empty string handled correctly.")

    @patch("data_bank_builder.requests.get")
    def test_get_upbit_price_valid_input(self, mock_get):
        """Test that valid input still works."""
        print("\nTesting Valid input...")
        mock_response = MagicMock()
        mock_response.json.return_value = [{'trade_price': 500}]
        mock_get.return_value = mock_response

        result = self.research_center.get_upbit_price("KRW-XRP")
        self.assertEqual(result, 500)
        mock_get.assert_called_once()
        print("SUCCESS: Valid input works correctly.")

if __name__ == "__main__":
    unittest.main()
