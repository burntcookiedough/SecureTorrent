import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import os

# Create models directory
if not os.path.exists('models'):
    os.makedirs('models')

print("🚀 Starting Model Retraining...")

# 1. Generate Synthetic Dataset (simulating network traffic)
# We need this because we don't have the original dataset, but we know the feature structure
# Features: src_bytes, dst_bytes, peer_count, seed_count, num_files, protocol_type, service, flag

n_samples = 5000
data = []

# Generate CLEAN traffic patterns
for _ in range(int(n_samples * 0.7)):
    data.append({
        'src_bytes': np.random.randint(100, 50000),
        'dst_bytes': np.random.randint(100, 50000),
        'peer_count': np.random.randint(1, 50),
        'seed_count': np.random.randint(10, 100),
        'num_files': np.random.randint(1, 10),
        'protocol_type': 'tcp',
        'service': 'http',
        'flag': 'SF',
        'is_malicious': 0
    })

# Generate MALICIOUS traffic patterns (Botnet/DDoS-like)
for _ in range(int(n_samples * 0.3)):
    data.append({
        'src_bytes': np.random.randint(1000, 1000000), # Large uploads
        'dst_bytes': np.random.randint(0, 1000),       # Small downloads
        'peer_count': np.random.randint(100, 1000),    # High peer count
        'seed_count': np.random.randint(0, 5),         # Low seed count
        'num_files': np.random.randint(50, 200),       # Many files
        'protocol_type': 'udp',
        'service': 'private',
        'flag': 'S0',
        'is_malicious': 1
    })

df = pd.DataFrame(data)
print(f"📊 Generated {len(df)} samples")

# 2. Preprocessing
le_dict = {}
for col in ['protocol_type', 'service', 'flag']:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    le_dict[col] = le

feature_names = ['src_bytes', 'dst_bytes', 'peer_count', 'seed_count', 'num_files', 'protocol_type', 'service', 'flag']
X = df[feature_names]
y = df['is_malicious']

# 3. Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. Model Training
print("🧠 Training Random Forest...")
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
model.fit(X_train_scaled, y_train)

# 6. Evaluation
y_pred = model.predict(X_test_scaled)
metrics = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred)
}

print(f"✅ Training Complete!")
print(f"   Accuracy:  {metrics['accuracy']:.4f}")
print(f"   Precision: {metrics['precision']:.4f}")
print(f"   Recall:    {metrics['recall']:.4f}")

# 7. Save Model
model_data = {
    'model': model,
    'scaler': scaler,
    'feature_names': feature_names,
    'le_dict': le_dict,
    'metrics': metrics
}

output_path = './models/malware_detector_latest.pkl'
with open(output_path, 'wb') as f:
    pickle.dump(model_data, f)

print(f"💾 Model saved to: {output_path}")
