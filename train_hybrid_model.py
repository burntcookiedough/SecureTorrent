"""
Hybrid Torrent Malware Detection Model Training
Based on notebook8db75a0105.ipynb
Generates realistic synthetic data with PE + Universal + YARA features
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import os

print("="*80)
print("🎯 HYBRID TORRENT MALWARE DETECTION MODEL")
print("   Realistic PE + Universal + YARA Features")
print("="*80)

# Create models directory
if not os.path.exists('models'):
    os.makedirs('models')

# ========== GENERATE SYNTHETIC PE-LIKE DATA ==========
print("\n📊 Generating synthetic dataset...")
n_samples = 5000
data = []

# Generate BENIGN samples (70%)
for _ in range(int(n_samples * 0.7)):
    data.append({
        # Basic PE features
        'file_size': np.random.randint(50000, 500000),
        'section_count': np.random.randint(3, 8),
        'entry_point': np.random.randint(1000, 10000),
        
        # Universal features
        'file_entropy_full': np.random.uniform(5.0, 6.5),
        'file_entropy_header': np.random.uniform(4.5, 6.0),
        'file_entropy_trailer': np.random.uniform(4.5, 6.0),
        'entropy_variance': np.random.uniform(0.3, 0.6),
        'null_byte_ratio': np.random.uniform(0.05, 0.15),
        'printable_char_ratio': np.random.uniform(0.30, 0.50),
        'byte_freq_std': np.random.uniform(60, 85),
        'unique_bytes': np.random.randint(180, 220),
        
        # Torrent-specific
        'download_progress': 1.0,
        'torrent_piece_count': np.random.randint(10, 50),
        
        'is_malicious': 0
    })

# Generate MALICIOUS samples (30%)
for _ in range(int(n_samples * 0.3)):
    data.append({
        # Basic PE features (packed/suspicious)
        'file_size': np.random.randint(100000, 2000000),
        'section_count': np.random.randint(8, 15),
        'entry_point': np.random.randint(5000, 50000),
        
        # Universal features (high entropy = packed)
        'file_entropy_full': np.random.uniform(7.0, 8.0),
        'file_entropy_header': np.random.uniform(6.8, 7.8),
        'file_entropy_trailer': np.random.uniform(6.8, 7.8),
        'entropy_variance': np.random.uniform(0.05, 0.25),  # Low variance
        'null_byte_ratio': np.random.uniform(0.01, 0.08),
        'printable_char_ratio': np.random.uniform(0.15, 0.30),
        'byte_freq_std': np.random.uniform(85, 110),
        'unique_bytes': np.random.randint(230, 256),
        
        # Torrent-specific
        'download_progress': 1.0,
        'torrent_piece_count': np.random.randint(50, 200),
        
        'is_malicious': 1
    })

df = pd.DataFrame(data)
print(f"Generated {len(df)} samples (Benign: {(df['is_malicious']==0).sum()}, Malicious: {(df['is_malicious']==1).sum()})")

# ========== ADD YARA RULE FEATURES ==========
print("\n🔍 Adding YARA rule features...")

# Rule 1: Suspicious Packer (high entropy OR low section count)
df['YARA_Suspicious_Packer'] = ((df['file_entropy_full'] > 7.0) | (df['section_count'] > 10)).astype(int)

# Rule 2: Ransomware Indicators (high entropy)
df['YARA_Ransomware_Indicators'] = (df['file_entropy_full'] > 6.9).astype(int)

# Rule 3: Dropper Behavior (small file with many sections)
df['YARA_Dropper_Behavior'] = ((df['file_size'] < 100000) & (df['section_count'] > 8)).astype(int)

# Rule 4: Suspicious Sections (unusual section count)
df['YARA_Suspicious_Sections'] = ((df['section_count'] > 12) | (df['section_count'] < 3)).astype(int)

# Rule 5: Network Malware (medium size, moderate entropy)
df['YARA_Network_Malware'] = (
    (df['file_size'] > 50000) & (df['file_size'] < 800000) &
    (df['file_entropy_full'] > 5.5) & (df['file_entropy_full'] < 6.9)
).astype(int)

# Rule 6: Obfuscation Patterns (low variance with high entropy)
df['YARA_Obfuscation_Patterns'] = (
    (df['entropy_variance'] < 0.25) & (df['file_entropy_full'] > 6.5)
).astype(int)

yara_features = [col for col in df.columns if col.startswith('YARA_')]
print(f"Created {len(yara_features)} YARA features")

# ========== PREPARE FEATURES ==========
feature_names = [col for col in df.columns if col != 'is_malicious']
X = df[feature_names]
y = df['is_malicious']

print(f"\n📦 FINAL FEATURE SET")
print(f"   Total Features: {len(feature_names)}")
print(f"   - PE-like: {len([f for f in feature_names if not f.startswith('YARA_')])}")
print(f"   - YARA Rules: {len(yara_features)}")

# ========== TRAIN/TEST SPLIT ==========
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ========== SCALING ==========
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"\nTraining: {X_train.shape[0]:,} | Test: {X_test.shape[0]:,}")

# ========== MODEL TRAINING ==========
print("\n🤖 Training Hybrid Random Forest...")
model = RandomForestClassifier(
    n_estimators=300, 
    max_depth=20, 
    random_state=42, 
    class_weight='balanced',
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)

# ========== EVALUATION ==========
y_pred = model.predict(X_test_scaled)
metrics = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred)
}

print(f"\n✅ Training Complete!")
print(f"   Accuracy:  {metrics['accuracy']:.4f}")
print(f"   Precision: {metrics['precision']:.4f}")
print(f"   Recall:    {metrics['recall']:.4f}")
print(f"   F1-Score:  {metrics['f1']:.4f}")

# ========== SAVE MODEL ==========
model_data = {
    'model': model,
    'scaler': scaler,
    'feature_names': feature_names,
    'le_dict': {},  # No label encoding needed for this version
    'metrics': metrics,
    'model_type': 'Hybrid_Torrent_Detector_Synthetic'
}

output_path = './models/torrent_malware_detector_realistic_hybrid.pkl'
with open(output_path, 'wb') as f:
    pickle.dump(model_data, f)

print(f"\n💾 Model saved to: {output_path}")
print("="*80)
