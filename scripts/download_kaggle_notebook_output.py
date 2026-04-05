"""
Download dataset from Kaggle Notebook Output
Uses Kaggle API to extract the preprocessed dataset
"""

import os
import subprocess
import sys
from pathlib import Path

# Configuration
NOTEBOOK_SLUG = "yashwithbehera/notebook3156cb2c66"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "kaggle_notebook_output"

def check_kaggle_auth():
    """Check if Kaggle API is properly configured"""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print("❌ kaggle.json not found!")
        print(f"📍 Expected location: {kaggle_json}")
        print("\n📝 To fix this:")
        print("1. Go to https://www.kaggle.com/settings/account")
        print("2. Scroll to 'API' section")
        print("3. Click 'Create New Token' to download kaggle.json")
        print(f"4. Place it in: {kaggle_json.parent}")
        return False
    
    print(f"✅ Found kaggle.json at: {kaggle_json}")
    return True

def install_kaggle():
    """Install kaggle package if not present"""
    try:
        import kaggle
        print("✅ Kaggle package already installed")
        return True
    except ImportError:
        print("📦 Installing kaggle package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "kaggle"])
        print("✅ Kaggle package installed")
        return True

def download_notebook_output():
    """Download notebook output files"""
    print(f"\n📥 Downloading output from notebook: {NOTEBOOK_SLUG}")
    print(f"📂 Saving to: {OUTPUT_DIR}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download using kaggle API
    try:
        cmd = f'kaggle kernels output {NOTEBOOK_SLUG} -p "{OUTPUT_DIR}"'
        print(f"\n🔧 Running: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\n✅ Download successful!")
            print(result.stdout)
            return True
        else:
            print("\n❌ Download failed!")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def list_downloaded_files():
    """List all downloaded files"""
    if not OUTPUT_DIR.exists():
        print("❌ Output directory doesn't exist")
        return
    
    files = list(OUTPUT_DIR.glob("*"))
    if not files:
        print("⚠️ No files found in output directory")
        return
    
    print(f"\n📁 Downloaded files ({len(files)}):")
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.2f} MB)")

def analyze_dataset():
    """Analyze the downloaded dataset"""
    print("\n🔍 Analyzing dataset...")
    
    # Look for CSV files
    csv_files = list(OUTPUT_DIR.glob("*.csv"))
    
    if not csv_files:
        print("⚠️ No CSV files found in output")
        return
    
    import pandas as pd
    
    for csv_file in csv_files:
        print(f"\n📊 Analyzing: {csv_file.name}")
        
        # Read first few rows to check structure
        try:
            df = pd.read_csv(csv_file, nrows=5)
            
            print(f"\n📏 Shape (first 5 rows): {df.shape}")
            print(f"\n📋 Columns ({len(df.columns)}):")
            print(df.columns.tolist())
            
            print(f"\n📄 First 3 rows:")
            print(df.head(3))
            
            print(f"\n🔢 Data types:")
            print(df.dtypes)
            
        except Exception as e:
            print(f"❌ Error reading {csv_file.name}: {e}")

def main():
    print("="*70)
    print("🚀 KAGGLE NOTEBOOK OUTPUT DOWNLOADER")
    print("="*70)
    
    # Step 1: Check authentication
    if not check_kaggle_auth():
        return
    
    # Step 2: Install kaggle package
    if not install_kaggle():
        return
    
    # Step 3: Download notebook output
    if not download_notebook_output():
        return
    
    # Step 4: List downloaded files
    list_downloaded_files()
    
    # Step 5: Analyze dataset
    analyze_dataset()
    
    print("\n" + "="*70)
    print("✅ DOWNLOAD COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    main()
