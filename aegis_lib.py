import os
import sys
import importlib.util
import ast
import warnings
import traceback
import urllib.parse

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    nn = None

warnings.filterwarnings('ignore')

class AegisValidator:
    """
    🛡️ [AegisValidator Class] - Safe Evolution Guardrails & Critical Thinking Module
    Validates code proposals and system commands before execution.
    """

    @staticmethod
    def validate_proposal(filepath, input_dim=38, check_model=True):
        """
        Validates the generated evolution proposal code before allowing execution.
        Checks:
        1. Python Syntax
        2. Input Dimension Consistency (must support 38 features) [If check_model=True]
        3. MPS Compatibility (if available) [If check_model=True]
        """
        print(f"\n🔍 [AegisValidator] Verifying Proposal: {filepath}")

        # 1. Syntax Check
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                source = f.read()
            ast.parse(source)
            print("   ✅ Syntax Check Passed.")
        except SyntaxError as e:
            print(f"   ❌ Syntax Error: {e}")
            return False
        except Exception as e:
            print(f"   ❌ File Read Error: {e}")
            return False

        if not check_model:
             print("   ℹ️ Model structure check skipped (Target is not a Brain module).")
             return True

        if torch is None:
             print("   ⚠️ Torch not installed. Skipping model structure check.")
             return False

        # 2. Dynamic Import & Structure Check
        try:
            spec = importlib.util.spec_from_file_location("aegis_evolution_proposal", filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules["aegis_evolution_proposal"] = module
            spec.loader.exec_module(module)

            if not hasattr(module, "AegisEvolution"):
                print("   ❌ Class 'AegisEvolution' not found.")
                return False

            ModelClass = getattr(module, "AegisEvolution")

            # 3. Input Dimension & MPS Compatibility Check
            device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
            try:
                # Attempt instantiation with strict input_size
                model = ModelClass(input_size=input_dim).to(device)

                # Dry run with dummy input to verify forward pass
                dummy_input = torch.randn(1, input_dim).to(device)
                _ = model(dummy_input)

                print(f"   ✅ Structure & MPS Compatibility Verified (Device: {device}).")
                return ModelClass
            except Exception as e:
                print(f"   ❌ Runtime Validation Failed (MPS/Dim): {e}")
                return False

        except Exception as e:
            print(f"   ❌ Import/Execution Error: {e}")
            return False

    @staticmethod
    def validate_command(command_text):
        """
        사령관의 명령을 분석하고 무조건 세션 검증 상태로 전환합니다.
        (자동 승인 로직을 완전히 제거함)
        """
        if isinstance(command_text, list):
            command_text = " ".join(command_text)

        # 1. 명령어를 URL 안전 형식으로 인코딩 (딥 링크용)
        encoded_command = urllib.parse.quote(command_text)
        session_url = f"https://jules.google.com/session?q={encoded_command}"

        # 2. 분석 결과 생성 (모든 명령을 '검증 필요'로 설정)
        # 이제 Low Risk라도 Auto-Approved가 절대 발생하지 않습니다.
        report = {
            "risk_level": "Verification Required",
            "impact_analysis": "Manual verification forced by Commander Isangjin.",
            "status": "Pending Session Review", # 자동 승인(Auto-Approved) 문구 삭제
            "session_link": session_url
        }

        return report

    @staticmethod
    def check_dangerous_keywords(command_text):
        """파괴적인 명령어에 대한 2차 경고 로직"""
        if isinstance(command_text, list):
            command_text = " ".join(command_text)

        dangerous = ["rm -rf", "delete", "destroy", "format"]
        for word in dangerous:
            if word in command_text.lower():
                return True
        return False

    @staticmethod
    def analyze_impact(action_description):
        """
        Performs a 'Critical Thinking' risk assessment on a requested action.
        This now strictly enforces session verification for all actions.
        """
        # Redirect to validate_command to enforce single source of truth
        return AegisValidator.validate_command(action_description)
