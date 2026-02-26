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

# --- NOW IMPORT ---
from data_bank_builder import AegisM5ResearchCenter

class TestTickerInjection(unittest.TestCase):
    def setUp(self):
        # Mock necessary dependencies for AegisM5ResearchCenter instantiation
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
    def test_get_upbit_price_secure_behavior(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = [{'trade_price': 100}]
        mock_get.return_value = mock_response

        # Call with a valid ticker
        ticker = "KRW-XRP"
        self.research_center.get_upbit_price(ticker)

        # Check what arguments were passed to requests.get
        args, kwargs = mock_get.call_args
        url = args[0]
        params = kwargs.get('params', {})

        # Verify URL is clean
        self.assertEqual(url, "https://api.upbit.com/v1/ticker")
        # Verify params contains the market correctly
        self.assertEqual(params.get('markets'), ticker)
        print(f"\n[Security Check] Correct URL and Params used.")

    @patch("requests.get")
    def test_get_upbit_price_validation_failure(self, mock_get):
        # Call with an invalid ticker (malicious injection attempt)
        # This contains characters not allowed by regex ^[A-Z0-9]+-[A-Z0-9]+$
        malicious_ticker = "KRW-XRP&malicious_param=true"
        result = self.research_center.get_upbit_price(malicious_ticker)

        # Verify it returns "N/A" and does NOT call requests.get
        self.assertEqual(result, "N/A")
        mock_get.assert_not_called()
        print(f"\n[Security Check] Malicious input blocked correctly.")
