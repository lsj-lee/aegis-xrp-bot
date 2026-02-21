import os
import sys
import importlib.util
import ast
import torch
import torch.nn as nn
import warnings
import traceback

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
    def validate_command(command):
        """
        Validates a shell command for safety.
        Returns: True if safe, False if unsafe.
        """
        if isinstance(command, list):
            cmd_str = " ".join(command)
        else:
            cmd_str = str(command)

        # Blacklist of dangerous commands/keywords
        dangerous_keywords = [
            "rm -rf", "mkfs", "dd if=", ":(){ :|:& };:", "shutdown", "reboot",
            "chmod 777", "chown root", "wget http", "curl http", # Prefer https
            "> /dev/sda", "> /dev/mem"
        ]

        for keyword in dangerous_keywords:
            if keyword in cmd_str:
                print(f"🛑 [AegisValidator] Unsafe Command Blocked: {cmd_str} (Reason: '{keyword}')")
                return False

        print(f"✅ [AegisValidator] Command Verified Safe: {cmd_str}")
        return True

    @staticmethod
    def analyze_impact(action_description):
        """
        Performs a 'Critical Thinking' risk assessment on a requested action.
        Returns a dictionary with 'risk_level' and 'message'.
        """
        action_lower = action_description.lower()

        # High Risk Keywords
        high_risk_keywords = ["delete", "destroy", "format", "wipe", "reset database", "force push"]
        # Medium Risk Keywords
        medium_risk_keywords = ["update", "modify", "change", "pull", "merge", "restart"]

        risk_level = "Low"
        message = "Routine operation. System stability expected to remain high."

        for keyword in high_risk_keywords:
            if keyword in action_lower:
                risk_level = "High"
                message = f"⚠️ CRITICAL WARNING: Action contains destructive keyword '{keyword}'. Proceed with extreme caution."
                break

        if risk_level == "Low":
            for keyword in medium_risk_keywords:
                if keyword in action_lower:
                    risk_level = "Medium"
                    message = f"ℹ️ Notice: Action involves system modification ('{keyword}'). Verify backups if necessary."
                    break

        print(f"🧠 [AegisValidator] Impact Analysis: {risk_level} Risk - {message}")
        # [Manual Verification Enforced] All commands require Jules session verification
        return {"risk_level": risk_level, "message": message, "requires_verification": True}
