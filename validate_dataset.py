import pandas as pd
import sys

try:
    print("Reading CSV...")
    df = pd.read_csv("archive/SOMLAP DATASET.csv")
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()[:5]} ...")
    
    # Check for NaN values
    print(f"NaN check: {df.isnull().sum().sum()} total NaNs")
    
    # Check label column
    if 'Malware' in df.columns:
        print(f"Malware counts: {df['Malware'].value_counts().to_dict()}")
    elif 'Label' in df.columns:
        print(f"Label counts: {df['Label'].value_counts().to_dict()}")
    else:
        print("Label column not found!")
        print(f"Last column: {df.columns[-1]}")
        
    print("Dataset looks OK structure-wise.")
except Exception as e:
    print(f"Error reading CSV: {e}")
    sys.exit(1)
