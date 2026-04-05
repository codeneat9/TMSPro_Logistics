"""
Robust Kaggle Dataset Downloader with Retry Logic
Downloads the Porto Taxi Trajectory dataset with automatic retries
"""

import os
import time
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# Configuration
DATASET = "crailtap/taxi-trajectory"
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

def download_with_retry():
    """Download dataset with retry logic"""
    api = KaggleApi()
    api.authenticate()
    
    print("=" * 60)
    print("🚕 Robust Kaggle Dataset Downloader")
    print("=" * 60)
    print(f"Dataset: {DATASET}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Max retries: {MAX_RETRIES}")
    print("=" * 60)
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"\n📥 Attempt {attempt}/{MAX_RETRIES}...")
            print("⏳ Downloading (this may take 10-30 minutes)...")
            
            # Download (Kaggle API handles resume automatically)
            api.dataset_download_files(
                DATASET,
                path=str(OUTPUT_DIR),
                unzip=True,
                quiet=False
            )
            
            print("\n✅ Download completed successfully!")
            
            # Verify files
            csv_files = list(OUTPUT_DIR.glob("*.csv"))
            if csv_files:
                for f in csv_files:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    print(f"✅ {f.name} ({size_mb:.2f} MB)")
                return True
            else:
                print("⚠️  No CSV files found after download")
                
        except KeyboardInterrupt:
            print("\n❌ Download cancelled by user")
            return False
            
        except Exception as e:
            print(f"\n❌ Error on attempt {attempt}: {str(e)}")
            
            if attempt < MAX_RETRIES:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)
            else:
                print("\n❌ All retry attempts failed")
                print("\n💡 Alternatives:")
                print("   1. Download manually from: https://www.kaggle.com/datasets/crailtap/taxi-trajectory")
                print("   2. Check your internet connection")
                print("   3. Try again later")
                return False
    
    return False

if __name__ == "__main__":
    success = download_with_retry()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Ready for preprocessing!")
        print("Next step: python scripts\\preprocess_data.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Download failed - see alternatives above")
        print("=" * 60)
