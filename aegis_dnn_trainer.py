import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import os
import warnings
warnings.filterwarnings('ignore')

class AegisDNN(nn.Module):
    def __init__(self, input_size):
        super(AegisDNN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    def forward(self, x): return self.network(x)

def train_aegis_model():
    print("\n🧠 AEGIS 3.0 [3단계] 시공간 심층 신경망(4D DNN) 두뇌 학습 시작...")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    
    data_path = os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv")
    df = pd.read_csv(data_path, index_col='Date', parse_dates=True).dropna()

    X = df.drop(columns=['Target_Buy_Signal', 'Future_XRP_3d'], errors='ignore')
    y = df['Target_Buy_Signal']

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_scaled, y)

    X_tensor = torch.tensor(X_resampled, dtype=torch.float32).to(device)
    y_tensor = torch.tensor(y_resampled.values, dtype=torch.float32).view(-1, 1).to(device)

    model = AegisDNN(input_size=X.shape[1]).to(device)
    criterion = nn.BCELoss()
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
    print(f"🎯 4D 시공간 학습 완료! 예측 정확도: {accuracy * 100:.2f}%")
    
    model_save_path = os.path.expanduser("~/Desktop/xrp_research/aegis_brain.pth")
    torch.save(model.state_dict(), model_save_path)
    print("="*50)

if __name__ == "__main__":
    train_aegis_model()