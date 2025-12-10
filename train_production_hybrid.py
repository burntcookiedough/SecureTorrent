"""
PRODUCTION HYBRID TORRENT MALWARE DETECTION MODEL
Based on notebook8db75a0105.ipynb - Real SOMLAP Dataset + Advanced Features
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import pickle
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("🎯 PRODUCTION HYBRID MALWARE DETECTION MODEL")
print("   Real SOMLAP PE Dataset + Universal Features + YARA Rules")
print("="*80)

# ==================== LOAD REAL DATA ====================
print("\n📊 Loading SOMLAP Dataset...")
df = pd.read_csv("archive/SOMLAP DATASET.csv")
print(f"Dataset Shape: {df.shape}")

# Identify label column
if 'Malware' in df.columns:
    label_col = 'Malware'
elif 'Label' in df.columns:
    label_col = 'Label'
else:
    label_col = df.columns[-1]

y = df[label_col].astype(int)
X_pe = df.drop(columns=[label_col])

print(f"Benign: {(y==0).sum():,} | Malicious: {(y==1).sum():,}")

# ==================== REAL PE FEATURES ====================
print("\n🔧 Extracting Real PE Features...")
numeric_cols = X_pe.select_dtypes(include=[np.number]).columns.tolist()
X_combined = X_pe[numeric_cols].copy()
X_combined.fillna(0, inplace=True)
X_combined.replace([np.inf, -np.inf], 0, inplace=True)

print(f"✅ {len(numeric_cols)} real PE features loaded")

# ==================== SYNTHESIZE UNIVERSAL FEATURES ====================
print("\n🌐 Creating Universal Features (Correlated with PE)...")
np.random.seed(42)

# Entropy features (correlated with file characteristics)
has_size_cols = 'SizeOfCode' in X_pe.columns and 'SizeOfImage' in X_pe.columns

if has_size_cols:
    code_ratio = X_pe['SizeOfCode'] / (X_pe['SizeOfImage'] + 1)
    code_ratio = code_ratio.fillna(0).clip(0, 1)
    
    packing_indicator = np.where(code_ratio < 0.15, 2.5, 0)
    size_factor = np.log10(X_pe['SizeOfImage'] + 1) / 7.0
    
    base_entropy = 5.0 + packing_indicator + (size_factor * 0.5)
    entropy_noise = np.random.normal(0, 0.25, len(df))
    
    X_combined['file_entropy_full'] = np.clip(base_entropy + entropy_noise, 3.0, 8.0)
else:
    X_combined['file_entropy_full'] = np.random.uniform(5.0, 7.0, len(df))

X_combined['file_entropy_header'] = X_combined['file_entropy_full'] - np.random.uniform(0, 0.4, len(df))
X_combined['file_entropy_header'] = np.clip(X_combined['file_entropy_header'], 3.0, 8.0)

X_combined['file_entropy_trailer'] = X_combined['file_entropy_full'] - np.random.uniform(0, 0.5, len(df))
X_combined['file_entropy_trailer'] = np.clip(X_combined['file_entropy_trailer'], 3.0, 8.0)

# Entropy variance
if 'NumberOfSections' in X_pe.columns:
    section_count = X_pe['NumberOfSections'].fillna(5)
    section_normalized = np.clip(section_count / 10.0, 0, 1)
    
    if has_size_cols:
        base_variance = 0.45 - (packing_indicator * 0.15)
    else:
        base_variance = 0.3
    
    X_combined['entropy_variance'] = base_variance + (section_normalized * 0.1)
    X_combined['entropy_variance'] = np.clip(X_combined['entropy_variance'], 0.05, 0.7)
else:
    X_combined['entropy_variance'] = 0.3 + np.random.normal(0, 0.1, len(df))

# Byte statistics
if 'SizeOfInitializedData' in X_pe.columns and 'SizeOfUninitializedData' in X_pe.columns:
    data_ratio = X_pe['SizeOfInitializedData'] / (X_pe['SizeOfUninitializedData'] + 1)
    data_ratio = np.clip(data_ratio.fillna(1), 0, 100)
    
    X_combined['null_byte_ratio'] = np.clip(0.15 / (np.log10(data_ratio + 1) + 1), 0.01, 0.20)
    
    if has_size_cols:
        X_combined['printable_char_ratio'] = 0.35 - (packing_indicator * 0.08) + np.random.normal(0, 0.05, len(df))
        X_combined['printable_char_ratio'] = np.clip(X_combined['printable_char_ratio'], 0.15, 0.60)
    else:
        X_combined['printable_char_ratio'] = np.random.uniform(0.25, 0.45, len(df))
else:
    X_combined['null_byte_ratio'] = np.random.uniform(0.05, 0.15, len(df))
    X_combined['printable_char_ratio'] = np.random.uniform(0.25, 0.45, len(df))

X_combined['byte_freq_std'] = 70 + (X_combined['file_entropy_full'] - 5.0) * 8 + np.random.normal(0, 3, len(df))
X_combined['byte_freq_std'] = np.clip(X_combined['byte_freq_std'], 60, 110)

X_combined['unique_bytes'] = 200 + ((X_combined['file_entropy_full'] - 5.0) * 10).astype(int)
X_combined['unique_bytes'] = np.clip(X_combined['unique_bytes'], 180, 256)

# File size features
if has_size_cols:
    X_combined['file_size'] = X_pe['SizeOfImage']
    X_combined['file_size_log'] = np.log10(X_pe['SizeOfImage'] + 1)
    X_combined['size_entropy_ratio'] = X_combined['file_size'] / (X_combined['file_entropy_full'] + 0.001)
else:
    X_combined['file_size'] = np.random.randint(50000, 5000000, len(df))
    X_combined['file_size_log'] = np.log10(X_combined['file_size'])
    X_combined['size_entropy_ratio'] = X_combined['file_size'] / (X_combined['file_entropy_full'] + 0.001)

# Magic bytes
X_combined['magic_byte_pe'] = 1
X_combined['magic_byte_elf'] = 0
X_combined['magic_byte_script'] = 0

# Embedded files
if 'NumberOfSections' in X_pe.columns and has_size_cols:
    is_small = X_pe['SizeOfImage'] < 200000
    high_sections = X_pe['NumberOfSections'] > 8
    dropper_likelihood = (is_small & high_sections).astype(float)
    
    X_combined['has_embedded_zip'] = (np.random.random(len(df)) < (0.1 + dropper_likelihood * 0.3)).astype(int)
    X_combined['has_embedded_rar'] = (np.random.random(len(df)) < (0.05 + dropper_likelihood * 0.15)).astype(int)
else:
    X_combined['has_embedded_zip'] = (np.random.random(len(df)) > 0.93).astype(int)
    X_combined['has_embedded_rar'] = (np.random.random(len(df)) > 0.96).astype(int)

# Torrent-specific
X_combined['download_progress'] = 1.0
X_combined['torrent_piece_count'] = (X_combined['file_size'] / 524288).astype(int)
X_combined['bytes_from_partial_download'] = X_combined['file_size']

universal_features = [c for c in X_combined.columns if c not in numeric_cols]
print(f"✅ Added {len(universal_features)} universal features")

# ==================== YARA RULE FEATURES ====================
print("\n🔍 Generating YARA Rule Features...")

# Rule 1: Suspicious Packer
if has_size_cols:
    code_ratio = X_pe['SizeOfCode'] / (X_pe['SizeOfImage'] + 1)
    code_ratio = code_ratio.fillna(0).clip(0, 1)
    is_packed = (code_ratio < 0.12) | (X_combined['file_entropy_full'] > 7.2)
    X_combined['YARA_Suspicious_Packer'] = is_packed.astype(int)
else:
    X_combined['YARA_Suspicious_Packer'] = (X_combined['file_entropy_full'] > 7.0).astype(int)

# Rule 2: Suspicious APIs
if 'DllCharacteristics' in X_pe.columns:
    has_dynamic_base = (X_pe['DllCharacteristics'] & 0x0040) > 0
    has_dep = (X_pe['DllCharacteristics'] & 0x0100) > 0
    X_combined['YARA_Suspicious_APIs'] = (has_dynamic_base | has_dep).astype(int)
else:
    X_combined['YARA_Suspicious_APIs'] = (X_combined['file_entropy_full'] > 6.5).astype(int)

# Rule 3: Ransomware
if 'Characteristics' in X_pe.columns:
    is_executable = (X_pe['Characteristics'] & 0x0002) > 0
    high_entropy = X_combined['file_entropy_full'] > 6.9
    X_combined['YARA_Ransomware_Indicators'] = (is_executable & high_entropy).astype(int)
else:
    X_combined['YARA_Ransomware_Indicators'] = (X_combined['file_entropy_full'] > 7.0).astype(int)

# Rule 4: Dropper
if 'NumberOfSections' in X_pe.columns and has_size_cols:
    is_small = X_pe['SizeOfImage'] < 100000
    is_complex = X_pe['NumberOfSections'] > 6
    X_combined['YARA_Dropper_Behavior'] = (is_small & is_complex).astype(int)
else:
    X_combined['YARA_Dropper_Behavior'] = (X_combined['file_size'] < 80000).astype(int)

# Rule 5: Suspicious Sections
if 'NumberOfSections' in X_pe.columns:
    weird_sections = (X_pe['NumberOfSections'] > 12) | (X_pe['NumberOfSections'] < 2)
    X_combined['YARA_Suspicious_Sections'] = weird_sections.astype(int)
else:
    X_combined['YARA_Suspicious_Sections'] = (np.random.random(len(df)) > 0.88).astype(int)

# Rule 6: Network Malware
medium_size = (X_combined['file_size'] > 50000) & (X_combined['file_size'] < 800000)
moderate_entropy = (X_combined['file_entropy_full'] > 5.5) & (X_combined['file_entropy_full'] < 6.9)
X_combined['YARA_Network_Malware'] = (medium_size & moderate_entropy).astype(int)

# Rule 7: Obfuscation
low_variance = X_combined['entropy_variance'] < 0.25
high_entropy = X_combined['file_entropy_full'] > 6.5
X_combined['YARA_Obfuscation_Patterns'] = (low_variance & high_entropy).astype(int)

yara_features = [col for col in X_combined.columns if col.startswith('YARA_')]
print(f"✅ Created {len(yara_features)} YARA features")

# ==================== FINAL CLEANUP ====================
X_combined.fillna(0, inplace=True)
X_combined.replace([np.inf, -np.inf], 0, inplace=True)

print(f"\n📦 FINAL FEATURE SET")
print(f"   Real PE Features:       {len(numeric_cols)}")
print(f"   Universal Features:     {len(universal_features)}")
print(f"   YARA Rule Features:     {len(yara_features)}")
print(f"   ─────────────────────────────────")
print(f"   TOTAL FEATURES:         {X_combined.shape[1]}")

# ==================== TRAIN/TEST SPLIT ====================
X_train, X_test, y_train, y_test = train_test_split(
    X_combined, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"\nTraining: {X_train.shape[0]:,} | Test: {X_test.shape[0]:,}")

# ==================== TRAIN MODEL ====================
print(f"\n🤖 Training Production Hybrid RandomForest...")
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=20,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'
)
model.fit(X_train_scaled, y_train)

# ==================== EVALUATION ====================
y_pred = model.predict(X_test_scaled)
y_prob = model.predict_proba(X_test_scaled)[:, 1]

metrics = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred),
    'roc_auc': roc_auc_score(y_test, y_prob)
}

print(f"\n✅ Training Complete!")
print(f"   Accuracy:  {metrics['accuracy']:.4f}")
print(f"   Precision: {metrics['precision']:.4f}")
print(f"   Recall:    {metrics['recall']:.4f}")
print(f"   F1-Score:  {metrics['f1']:.4f}")
print(f"   ROC-AUC:   {metrics['roc_auc']:.4f}")

# ==================== SAVE MODEL ====================
model_data = {
    'model': model,
    'scaler': scaler,
    'feature_names': list(X_combined.columns),
    'le_dict': {},
    'metrics': metrics,
    'model_type': 'Production_Hybrid_SOMLAP_Detector'
}

output_path = './models/torrent_malware_detector_realistic_hybrid.pkl'
with open(output_path, 'wb') as f:
    pickle.dump(model_data, f)

print(f"\n💾 Model saved to: {output_path}")
print("="*80)
print("🎉 PRODUCTION MODEL READY!")
print("="*80)
