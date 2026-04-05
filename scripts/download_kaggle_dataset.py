"""
Download Kaggle Dataset - Porto Taxi Trajectory or Similar
Uses Kaggle API to download specific files without downloading entire archive
"""

import os
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# Configuration
DATASET = "crailtap/taxi-trajectory"  # Porto Taxi Trajectory dataset
# Alternative datasets you can use:
# DATASET = "jsyousef/data-of-10000-taxi-trips-in-portugal"
# DATASET = "c/geolife-trajectories-1-3"

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def authenticate_kaggle():
    """Authenticate with Kaggle API using kaggle.json"""
    api = KaggleApi()
    api.authenticate()
    print("✅ Kaggle API authenticated successfully")
    return api

def list_dataset_files(api, dataset):
    """List all files in the dataset"""
    print(f"\n📂 Listing files in dataset: {dataset}")
    print("-" * 60)
    
    files = api.dataset_list_files(dataset).files
    for i, f in enumerate(files, 1):
        size_mb = f.size / (1024 * 1024)
        print(f"{i}. {f.name:<40} ({size_mb:.2f} MB)")
    
    print("-" * 60)
    return files

def download_dataset(api, dataset, output_dir, specific_file=None):
    """
    Download dataset or specific file
    
    Args:
        api: KaggleApi instance
        dataset: Dataset identifier (owner/dataset-name)
        output_dir: Directory to save files
        specific_file: Optional specific file to download (otherwise downloads all)
    """
    print(f"\n⬇️  Downloading from {dataset}...")
    print(f"📁 Output directory: {output_dir}")
    
    if specific_file:
        print(f"📄 Downloading specific file: {specific_file}")
        api.dataset_download_file(
            dataset=dataset,
            file_name=specific_file,
            path=str(output_dir)
        )
        print(f"✅ Downloaded: {specific_file}")
    else:
        print("📦 Downloading entire dataset...")
        api.dataset_download_files(
            dataset=dataset,
            path=str(output_dir),
            unzip=True
        )
        print("✅ Dataset downloaded and extracted")

def main():
    """Main execution"""
    print("=" * 60)
    print("🚕 Kaggle Dataset Downloader for TMS AI Project")
    print("=" * 60)
    
    # Authenticate
    api = authenticate_kaggle()
    
    # List files
    files = list_dataset_files(api, DATASET)
    
    # Download strategy options:
    # Option 1: Download all files
    download_dataset(api, DATASET, OUTPUT_DIR)
    
    # Option 2: Download specific file (uncomment and modify as needed)
    # specific_file = "train.csv"  # Replace with actual filename from list
    # download_dataset(api, DATASET, OUTPUT_DIR, specific_file=specific_file)
    
    print("\n" + "=" * 60)
    print("✅ Download complete!")
    print(f"📂 Files saved to: {OUTPUT_DIR}")
    print("=" * 60)
    
    # List downloaded files
    print("\n📋 Downloaded files:")
    for f in OUTPUT_DIR.iterdir():
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
