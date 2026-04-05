"""
Analyze the preprocessed taxi delay dataset
Check column structure, data types, and prepare for training
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Dataset path
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATASET_FILE = DATA_DIR / "preprocessed_taxi_delay_dataset1.csv"

def analyze_dataset():
    print("="*70)
    print("🔍 DATASET ANALYSIS")
    print("="*70)
    
    print(f"\n📂 Loading dataset from: {DATASET_FILE}")
    
    # Load first few rows to check structure
    print("\n⏳ Loading first 1000 rows...")
    df_sample = pd.read_csv(DATASET_FILE, nrows=1000)
    
    print(f"\n📏 Sample Shape: {df_sample.shape}")
    print(f"   Rows: {df_sample.shape[0]:,}")
    print(f"   Columns: {df_sample.shape[1]:,}")
    
    print(f"\n📋 Column Names ({len(df_sample.columns)}):")
    for i, col in enumerate(df_sample.columns, 1):
        print(f"   {i:2d}. {col}")
    
    print(f"\n🔢 Data Types:")
    print(df_sample.dtypes)
    
    print(f"\n📊 First 5 Rows:")
    print(df_sample.head())
    
    print(f"\n📈 Statistical Summary:")
    print(df_sample.describe())
    
    # Check for target variable
    possible_targets = ['delay', 'delayed', 'is_delayed', 'target', 'label']
    found_target = None
    for col in df_sample.columns:
        if col.lower() in possible_targets:
            found_target = col
            break
    
    if found_target:
        print(f"\n🎯 Target Variable Found: '{found_target}'")
        print(f"   Distribution:")
        print(df_sample[found_target].value_counts())
        print(f"   Percentage:")
        print(df_sample[found_target].value_counts(normalize=True) * 100)
    else:
        print(f"\n⚠️ No obvious target variable found")
        print(f"   Possible candidates: {[col for col in df_sample.columns if 'delay' in col.lower()]}")
    
    # Check missing values
    print(f"\n🔍 Missing Values:")
    missing = df_sample.isnull().sum()
    if missing.sum() > 0:
        print(missing[missing > 0])
    else:
        print("   No missing values in sample")
    
    # Get full dataset size without loading it all
    print(f"\n📦 Getting full dataset info...")
    chunk_size = 100000
    total_rows = 0
    
    for chunk in pd.read_csv(DATASET_FILE, chunksize=chunk_size):
        total_rows += len(chunk)
    
    print(f"   Total rows: {total_rows:,}")
    print(f"   Total columns: {len(df_sample.columns)}")
    print(f"   Estimated size: {total_rows * len(df_sample.columns) * 8 / (1024**3):.2f} GB in memory")
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    analyze_dataset()
