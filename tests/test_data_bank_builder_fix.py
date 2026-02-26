import sys
import os
import importlib
from unittest.mock import MagicMock, patch
import pytest

# Define mock exceptions
class MockException(Exception):
    pass

class MockAPIError(MockException):
    pass

class MockSpreadsheetNotFound(MockException):
    pass

class MockWorksheetNotFound(MockException):
    pass

@pytest.fixture
def mock_dependencies():
    # Create mocks
    mock_gspread = MagicMock()
    mock_gspread.exceptions.APIError = MockAPIError
    mock_gspread.exceptions.SpreadsheetNotFound = MockSpreadsheetNotFound
    mock_gspread.exceptions.WorksheetNotFound = MockWorksheetNotFound

    mock_modules = {
        'gspread': mock_gspread,
        'google.oauth2.service_account': MagicMock(),
        'yfinance': MagicMock(),
        'pandas': MagicMock(),
        'numpy': MagicMock(),
        'requests': MagicMock(),
        'dotenv': MagicMock(),
        'sklearn': MagicMock(),
        'sklearn.ensemble': MagicMock(),
    }

    # Save original data_bank_builder if it exists
    original_module = sys.modules.get('data_bank_builder')
    if original_module:
        del sys.modules['data_bank_builder']

    # Patch sys.modules with mocks
    with patch.dict(sys.modules, mock_modules):
        # Import data_bank_builder to use the mocks
        # Since we removed it from sys.modules, this creates a new module object
        import data_bank_builder
        yield mock_gspread, data_bank_builder

    # Restore original module to avoid polluting other tests
    if original_module:
        sys.modules['data_bank_builder'] = original_module
    else:
        # If it wasn't there before, ensure it is removed
        if 'data_bank_builder' in sys.modules:
            del sys.modules['data_bank_builder']

def test_worksheet_not_found_creates_new_sheet(mock_dependencies):
    mock_gspread, data_bank_builder = mock_dependencies

    # Setup mocks
    with patch('data_bank_builder.yf') as mock_yf, \
         patch('data_bank_builder.requests') as mock_requests, \
         patch('data_bank_builder.RandomForestRegressor'), \
         patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True), \
         patch('data_bank_builder.Credentials.from_service_account_file'):

        mock_yf.download.return_value = MagicMock()
        mock_requests.get.return_value.json.return_value = [{'trade_price': 100}]

        # Instantiate
        collector = data_bank_builder.AegisM5ResearchCenter("TestSheet", "dummy_key.json")
        collector.clean_df = MagicMock(return_value=MagicMock())
        collector.run_m5_machine_learning = MagicMock(return_value=(100, "Reason"))

        mock_spreadsheet = MagicMock()
        collector.client.open.return_value = mock_spreadsheet

        # Simulate WorksheetNotFound
        # We must use the exception class from the MOCKED gspread
        mock_spreadsheet.worksheet.side_effect = mock_gspread.exceptions.WorksheetNotFound("Not found")

        # Action
        collector.collect_and_relay()

        # Verify add_worksheet is called
        mock_spreadsheet.add_worksheet.assert_called_once_with(title="AEGIS_ML_Storage", rows="10", cols="6")

def test_api_error_does_not_create_sheet(mock_dependencies):
    mock_gspread, data_bank_builder = mock_dependencies

    with patch('data_bank_builder.yf') as mock_yf, \
         patch('data_bank_builder.requests') as mock_requests, \
         patch('data_bank_builder.RandomForestRegressor'), \
         patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True), \
         patch('data_bank_builder.Credentials.from_service_account_file'):

        mock_yf.download.return_value = MagicMock()
        mock_requests.get.return_value.json.return_value = [{'trade_price': 100}]

        collector = data_bank_builder.AegisM5ResearchCenter("TestSheet", "dummy_key.json")
        collector.clean_df = MagicMock(return_value=MagicMock())
        collector.run_m5_machine_learning = MagicMock(return_value=(100, "Reason"))

        mock_spreadsheet = MagicMock()
        collector.client.open.return_value = mock_spreadsheet

        # Simulate APIError
        mock_spreadsheet.worksheet.side_effect = mock_gspread.exceptions.APIError("API Failure")

        # Action
        collector.collect_and_relay()

        # Verify add_worksheet is NOT called
        mock_spreadsheet.add_worksheet.assert_not_called()

def test_unexpected_error_propagates(mock_dependencies):
    mock_gspread, data_bank_builder = mock_dependencies

    with patch('data_bank_builder.yf') as mock_yf, \
         patch('data_bank_builder.requests') as mock_requests, \
         patch('data_bank_builder.RandomForestRegressor'), \
         patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True), \
         patch('data_bank_builder.Credentials.from_service_account_file'):

        mock_yf.download.return_value = MagicMock()
        mock_requests.get.return_value.json.return_value = [{'trade_price': 100}]

        collector = data_bank_builder.AegisM5ResearchCenter("TestSheet", "dummy_key.json")
        collector.clean_df = MagicMock(return_value=MagicMock())
        collector.run_m5_machine_learning = MagicMock(return_value=(100, "Reason"))

        mock_spreadsheet = MagicMock()
        collector.client.open.return_value = mock_spreadsheet

        # Simulate unexpected RuntimeError
        mock_spreadsheet.worksheet.side_effect = RuntimeError("Something bad happened")

        # Action
        with pytest.raises(RuntimeError, match="Something bad happened"):
            collector.collect_and_relay()

        # Verify add_worksheet is NOT called
        mock_spreadsheet.add_worksheet.assert_not_called()
