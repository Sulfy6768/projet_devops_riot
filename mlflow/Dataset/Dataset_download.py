"""
Dataset Download Script
=======================

Downloads the League of Legends dataset from Google Drive using gdown.
The dataset is saved to the Immutable folder.

Usage:
    python Dataset_download.py [--force]
"""

import os
import gdown

# ============================================
# Configuration
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMMUTABLE_DIR = os.path.join(BASE_DIR, "Immutable")

# Google Drive folder URL containing the CSV files
DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH"


def download_dataset(force: bool = False) -> bool:
    """
    Download the dataset from Google Drive.
    
    Args:
        force: If True, delete existing files and re-download
        
    Returns:
        True if download was successful, False otherwise
    """
    print("=" * 60)
    print("Dataset Download")
    print("=" * 60)
    
    # Create directories if they don't exist
    os.makedirs(IMMUTABLE_DIR, exist_ok=True)
    
    # Check if dataset already exists
    existing_files = [f for f in os.listdir(IMMUTABLE_DIR) if f.endswith('.csv')]
    
    if existing_files and not force:
        print(f"✓ Dataset already exists ({len(existing_files)} CSV files found)")
        print("  Use --force to re-download")
        return True
    
    if force and existing_files:
        print(f"⚠️  Removing {len(existing_files)} existing files...")
        for f in existing_files:
            os.remove(os.path.join(IMMUTABLE_DIR, f))
    
    print(f"\n📥 Downloading dataset from Google Drive...")
    print(f"   URL: {DRIVE_FOLDER_URL}")
    print(f"   Destination: {IMMUTABLE_DIR}")
    
    try:
        # Download the folder
        gdown.download_folder(
            url=DRIVE_FOLDER_URL,
            output=IMMUTABLE_DIR,
            quiet=False,
            use_cookies=False
        )
        
        # Verify download
        downloaded_files = [f for f in os.listdir(IMMUTABLE_DIR) if f.endswith('.csv')]
        
        if downloaded_files:
            print(f"\n✅ Download complete!")
            print(f"   {len(downloaded_files)} CSV files downloaded:")
            for f in sorted(downloaded_files):
                size_mb = os.path.getsize(os.path.join(IMMUTABLE_DIR, f)) / 1_048_576
                print(f"     - {f} ({size_mb:.1f} MB)")
            return True
        else:
            print("\n❌ No CSV files were downloaded")
            return False
            
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download LoL dataset from Google Drive")
    parser.add_argument("--force", "-f", action="store_true", 
                        help="Force re-download even if files exist")
    args = parser.parse_args()
    
    success = download_dataset(force=args.force)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
