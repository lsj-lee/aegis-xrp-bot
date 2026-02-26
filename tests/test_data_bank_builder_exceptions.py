import sys
from unittest.mock import MagicMock

# Mock exceptions must inherit from BaseException
class MockException(Exception):
    pass

# Mock modules that might not be installed
mock_gspread = MagicMock()
mock_gspread.exceptions.APIError = MockException
mock_gspread.exceptions.SpreadsheetNotFound = MockException
mock_gspread.exceptions.WorksheetNotFound = MockException
sys.modules['gspread'] = mock_gspread

sys.modules['google.oauth2.service_account'] = MagicMock()
sys.modules['yfinance'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.ensemble'] = MagicMock()

import pytest
from unittest.mock import patch
import os

# Ensure data_bank_builder can be imported
sys.path.append(os.getcwd())

def test_collect_and_relay_swallows_type_error():
    # Patch dependencies EXCEPT gspread (handled by sys.modules)
    with patch('data_bank_builder.yf') as mock_yf, \
         patch('data_bank_builder.requests') as mock_requests, \
         patch('data_bank_builder.RandomForestRegressor') as mock_rf, \
         patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True), \
         patch('data_bank_builder.Credentials.from_service_account_file'):

        # Setup mocks to avoid failures before the target line
        mock_yf.download.return_value = MagicMock()
        mock_requests.get.return_value.json.return_value = [{'trade_price': 100}]

        from data_bank_builder import AegisM5ResearchCenter

        # Verify that AegisM5ResearchCenter sees our mocked exceptions
        import gspread
        assert issubclass(gspread.exceptions.APIError, BaseException)

        collector = AegisM5ResearchCenter("TestSheet", "dummy_key.json")

        # Mock methods to simplify flow
        collector.clean_df = MagicMock(return_value=MagicMock())
        collector.run_m5_machine_learning = MagicMock(return_value=(100, "Reason"))

        # Mock the client.open to raise TypeError
        # This simulates a bug in the code (e.g. passing wrong arguments)
        collector.client.open.side_effect = TypeError("This is a simulated bug!")

        # The new implementation should propagate TypeError
        with pytest.raises(TypeError, match="This is a simulated bug!"):
            collector.collect_and_relay()
