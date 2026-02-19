import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import os
import sys
import importlib.util
import ast
import warnings
import traceback
import shutil

warnings.filterwarnings('ignore')

# 🛡️ [AegisValidator Class] - Safe Evolution Guardrails
class AegisValidator:
    """
    Validates the generated evolution proposal code before allowing execution.
    Checks:
    1. Python Syntax
    2. Input Dimension Consistency (must support 38 features)
    3. MPS Compatibility (if available)
    """
    @staticmethod
    def validate_proposal(filepath, input_dim=38):
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

# 🧬 Standard AEGIS Architecture (Fallback / Baseline)
class AegisEvolution(nn.Module):
    def __init__(self, input_size, d_model=128, nhead=4, num_layers=3, dropout=0.2):
        super(AegisEvolution, self).__init__()
        self.feature_embedding = nn.Sequential(
            nn.Linear(input_size, d_model),
            nn.LayerNorm(d_model),
            nn.GELU()
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model*4,
            dropout=dropout, batch_first=True, activation='gelu'
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.Linear(d_model, 64), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(64, 1), nn.Sigmoid()
        )

    def forward(self, x):
        x = self.feature_embedding(x)
        x = x.unsqueeze(1)
        x = self.transformer_encoder(x)
        x = x.squeeze(1)
        return self.head(x)

def train_aegis_model():
    print("\n🧠 AEGIS 4.0 [3단계] Validated Self-Evolution Loop 시작...")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    
    try:
        # 1. Load Data
        data_path = os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv")
        if not os.path.exists(data_path):
            data_path = "ml_ready_data.csv"

        if not os.path.exists(data_path):
            print(f"⚠️ Data not found: {data_path}")
            return

        df = pd.read_csv(data_path, index_col='Date', parse_dates=True).dropna()
        X = df.drop(columns=['Target_Buy_Signal', 'Future_XRP_3d'], errors='ignore')
        y = df['Target_Buy_Signal']

        input_dim = X.shape[1]
        print(f"📊 Input Features: {input_dim}")

        # Scale & SMOTE
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        smote = SMOTE(random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X_scaled, y)

        X_tensor = torch.tensor(X_resampled, dtype=torch.float32).to(device)
        y_tensor = torch.tensor(y_resampled.values, dtype=torch.float32).view(-1, 1).to(device)

        # 2. Dynamic Engine Swapping Logic
        proposal_path = "aegis_evolution_proposal.py"
        best_model_class = AegisEvolution # Default to standard
        model_source = "Standard Stable Engine"

        if os.path.exists(proposal_path):
            validated_class = AegisValidator.validate_proposal(proposal_path, input_dim=input_dim)
            if validated_class:
                print("✨ New Evolution Proposal Accepted! Testing Performance...")
                best_model_class = validated_class
                model_source = "New Evolution Proposal"
            else:
                print("⚠️ Proposal Validation Failed. Rolling back to Standard Engine.")

        # 3. Train & Evaluate
        model = best_model_class(input_size=input_dim).to(device)
        criterion = nn.BCELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        # Calculate Baseline Loss (from existing file if possible, else 999)
        model_save_path = os.path.expanduser("~/Desktop/xrp_research/aegis_brain.pth")
        if not os.path.exists(os.path.dirname(model_save_path)):
            model_save_path = "aegis_brain.pth"

        old_loss = 999.0
        if os.path.exists(model_save_path):
            try:
                # Load old model to compare
                old_model = AegisEvolution(input_size=input_dim).to(device)
                old_model.load_state_dict(torch.load(model_save_path, map_location=device))
                old_model.eval()
                with torch.no_grad():
                    old_out = old_model(X_tensor)
                    old_loss = criterion(old_out, y_tensor).item()
                print(f"📉 Existing Model Loss: {old_loss:.6f}")
            except Exception as e:
                print(f"⚠️ Could not evaluate old model ({e}). Treating as fresh start.")

        print(f"🚀 Training {model_source}...")
        epochs = 500
        for epoch in range(1, epochs + 1):
            model.train()
            optimizer.zero_grad()
            outputs = model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            if epoch % 100 == 0:
                print(f"   ▶ Epoch [{epoch}/{epochs}], Loss: {loss.item():.4f}")

        final_loss = loss.item()
        print(f"🏁 New Model Final Loss: {final_loss:.6f}")

        # 4. Compare & Commit
        if final_loss < old_loss:
            print(f"✅ IMPROVEMENT DETECTED ({old_loss:.6f} -> {final_loss:.6f}). Committing New Brain.")
            torch.save(model.state_dict(), model_save_path)
            print(f"💾 Saved to {model_save_path}")

            # Adopt Code as well (Optional but recommended for consistency)
            if model_source == "New Evolution Proposal":
                try:
                    shutil.copy(proposal_path, "aegis_evolution_active.py")
                    print("🧬 Evolution Code Adopted as 'aegis_evolution_active.py'")
                except Exception as e:
                    print(f"⚠️ Failed to backup evolution code: {e}")
        else:
            print(f"🛑 NO IMPROVEMENT ({old_loss:.6f} -> {final_loss:.6f}). Discarding New Brain.")
            # If we were trying a proposal and it failed, we might want to ensure the file on disk is the old one.
            # Since we haven't overwritten it yet, we are good.
            # Unless we didn't have a file to begin with, then we should save the new one anyway?
            if old_loss == 999.0:
                 print("   (First run, saving anyway)")
                 torch.save(model.state_dict(), model_save_path)

    except Exception as e:
        print(f"🔥 CRITICAL ERROR in Training Loop: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    train_aegis_model()
