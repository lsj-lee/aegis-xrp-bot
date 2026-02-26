import sys
from unittest.mock import MagicMock, patch
import pytest
import os

# Mock exceptions must inherit from BaseException
class MockException(Exception):
    pass

@pytest.fixture
def mock_dependencies():
    """Patches sys.modules to mock dependencies before importing data_bank_builder."""
    # Ensure root path is in sys.path
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    # Create Mock Objects
    mock_gspread = MagicMock()
    mock_gspread.exceptions.APIError = MockException
    mock_gspread.exceptions.SpreadsheetNotFound = MockException
    mock_gspread.exceptions.WorksheetNotFound = MockException

    # Dependencies to mock
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

    # We must remove data_bank_builder if it is already in sys.modules
    # because it might have imported unmocked modules or old mocks.
    if 'data_bank_builder' in sys.modules:
        del sys.modules['data_bank_builder']

    with patch.dict(sys.modules, mock_modules):
        # Now import data_bank_builder inside the patch context
        import data_bank_builder
        yield data_bank_builder, mock_gspread

def test_worksheet_not_found_creates_new_worksheet(mock_dependencies):
    module, mock_gspread = mock_dependencies

    # Patch dependencies used inside the module functions or init
    with patch('data_bank_builder.yf') as mock_yf, \
         patch('data_bank_builder.requests') as mock_requests, \
         patch('data_bank_builder.RandomForestRegressor') as mock_rf, \
         patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True), \
         patch('data_bank_builder.Credentials.from_service_account_file'):

        # Instantiate collector
        collector = module.AegisM5ResearchCenter("TestSheet", "dummy_key.json")
        collector.clean_df = MagicMock(return_value=MagicMock())
        collector.run_m5_machine_learning = MagicMock(return_value=(100, "Reason"))

        # Setup mocks for collect_and_relay
        mock_spreadsheet = MagicMock()
        collector.client.open.return_value = mock_spreadsheet

        # Simulate WorksheetNotFound when accessing worksheet
        mock_spreadsheet.worksheet.side_effect = mock_gspread.exceptions.WorksheetNotFound("Sheet not found")

        # Setup add_worksheet mock
        mock_new_sheet = MagicMock()
        mock_spreadsheet.add_worksheet.return_value = mock_new_sheet

        # Call collect_and_relay
        collector.collect_and_relay()

        # Verify add_worksheet was called
        mock_spreadsheet.add_worksheet.assert_called_once_with(title="AEGIS_ML_Storage", rows="10", cols="6")
        mock_new_sheet.clear.assert_called_once()

def test_unexpected_exception_propagates(mock_dependencies):
    module, mock_gspread = mock_dependencies

    with patch('data_bank_builder.yf') as mock_yf, \
         patch('data_bank_builder.requests') as mock_requests, \
         patch('data_bank_builder.RandomForestRegressor') as mock_rf, \
         patch('os.path.isfile', return_value=True), \
         patch('os.access', return_value=True), \
         patch('data_bank_builder.Credentials.from_service_account_file'):

        # Instantiate collector
        collector = module.AegisM5ResearchCenter("TestSheet", "dummy_key.json")
        collector.clean_df = MagicMock(return_value=MagicMock())
        collector.run_m5_machine_learning = MagicMock(return_value=(100, "Reason"))

        # Setup mocks for collect_and_relay
        mock_spreadsheet = MagicMock()
        collector.client.open.return_value = mock_spreadsheet

        # Simulate unexpected exception (RuntimeError) when accessing worksheet
        mock_spreadsheet.worksheet.side_effect = RuntimeError("Unexpected Error!")

        # Verify that RuntimeError propagates and is NOT caught
        with pytest.raises(RuntimeError, match="Unexpected Error!"):
            collector.collect_and_relay()

        # Verify add_worksheet was NOT called
        mock_spreadsheet.add_worksheet.assert_not_called()
