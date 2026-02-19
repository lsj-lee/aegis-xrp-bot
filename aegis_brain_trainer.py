import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import os
import warnings
warnings.filterwarnings('ignore')

# 🧬 AEGIS Evolution Architecture (Transformer/TFT Based)
class AegisEvolution(nn.Module):
    def __init__(self, input_size, d_model=128, nhead=4, num_layers=3, dropout=0.2):
        super(AegisEvolution, self).__init__()

        # Feature Embedding Layer (Dense -> High Dim)
        self.feature_embedding = nn.Sequential(
            nn.Linear(input_size, d_model),
            nn.LayerNorm(d_model),
            nn.GELU()
        )

        # Transformer Encoder Block (Self-Attention + FeedForward)
        # batch_first=True ensures input is (Batch, Seq, Feature)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model*4,
            dropout=dropout,
            batch_first=True,
            activation='gelu'
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Final Output Head (Value Projection)
        self.head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        # x: (Batch, Input_Size)

        # 1. Embed Features
        x = self.feature_embedding(x) # -> (Batch, d_model)

        # 2. Add Sequence Dimension for Transformer (SeqLen=1)
        x = x.unsqueeze(1) # -> (Batch, 1, d_model)

        # 3. Apply Transformer Encoder
        x = self.transformer_encoder(x) # -> (Batch, 1, d_model)

        # 4. Remove Sequence Dimension
        x = x.squeeze(1) # -> (Batch, d_model)

        # 5. Output Probability
        return self.head(x)

def train_aegis_model():
    print("\n🧠 AEGIS 4.0 [3단계] 시공간 트랜스포머(Evolution) 두뇌 학습 시작...")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    
    data_path = os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv")
    if not os.path.exists(data_path):
        data_path = "ml_ready_data.csv"

    if not os.path.exists(data_path):
        print(f"⚠️ 학습 데이터({data_path})를 찾을 수 없습니다. 전처리 스크립트를 먼저 실행하세요.")
        return

    df = pd.read_csv(data_path, index_col='Date', parse_dates=True).dropna()

    X = df.drop(columns=['Target_Buy_Signal', 'Future_XRP_3d'], errors='ignore')
    y = df['Target_Buy_Signal']

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_scaled, y)

    X_tensor = torch.tensor(X_resampled, dtype=torch.float32).to(device)
    y_tensor = torch.tensor(y_resampled.values, dtype=torch.float32).view(-1, 1).to(device)

    # Instantiate the new Evolution model
    model = AegisEvolution(input_size=X.shape[1]).to(device)
    criterion = nn.BCELoss()
    # Increased learning rate slightly for Transformer or kept same?
    # Adam usually works well with 0.001, but Transformers might need warmup.
    # Keeping simple for now as per "grafting" request.
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    epochs = 500
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()
        if epoch % 100 == 0:
            print(f"   ▶ Epoch [{epoch}/{epochs}], 오차율(Loss): {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        predicted = model(X_tensor)
        accuracy = ((predicted >= 0.5).float() == y_tensor).sum().item() / y_tensor.size(0)

    print("="*50)
    print(f"🎯 4D Evolution 학습 완료! 예측 정확도: {accuracy * 100:.2f}%")
    
    model_save_path = os.path.expanduser("~/Desktop/xrp_research/aegis_brain.pth")

    # 폴더가 없으면 현재 경로에 저장 (Fallback)
    if not os.path.exists(os.path.dirname(model_save_path)):
        model_save_path = "aegis_brain.pth"

    torch.save(model.state_dict(), model_save_path)
    print(f"💾 모델 저장 완료: {model_save_path}")
    print("="*50)

if __name__ == "__main__":
    train_aegis_model()
