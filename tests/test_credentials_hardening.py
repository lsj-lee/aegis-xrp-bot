import os

def test_no_hardcoded_creds_xrp_coin_json():
    """
    Regression test to ensure 'creds xrp coin.json' is not hardcoded in data_bank_builder.py.
    This file was previously identified as having this vulnerability.
    """
    filepath = "data_bank_builder.py"
    if not os.path.exists(filepath):
        # If file is moved, this test might need update, but it shouldn't fail silently
        assert False, f"{filepath} not found"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for the specific hardcoded string
    assert "creds xrp coin.json" not in content, "Found hardcoded 'creds xrp coin.json' in data_bank_builder.py"

def test_main_uses_env_var_for_creds():
    """
    Static analysis to ensure GCP_CREDS_PATH environment variable is used in data_bank_builder.py
    """
    filepath = "data_bank_builder.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'os.getenv("GCP_CREDS_PATH")' in content or "os.getenv('GCP_CREDS_PATH')" in content, \
        "data_bank_builder.py should use os.getenv('GCP_CREDS_PATH')"
