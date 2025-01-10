import argparse
import os
import glob
import time
from tqdm import tqdm

def delete_files(h5_path, zip_path):
    today = time.strftime('%Y%m%d')
    yesterday = time.strftime('%Y%m%d', time.gmtime(time.time() - 86400))
    for path in [h5_path, zip_path]:
        for root, dirs, files in tqdm(os.walk(path), desc=f"Processing {path}"):
            for file in tqdm(files, desc=f"Processing {root}",leave=False):
                file_path = os.path.join(root, file)
                file_time = time.strftime('%Y%m%d', time.gmtime(os.path.getmtime(file_path)))
                if file_time == yesterday or file_time == today:
                    if path == h5_path and file.endswith('.h5'):
                        tqdm.write(f"Deleting .h5 file: {file_path}")
                        os.remove(file_path)
                    elif path == zip_path and file.endswith('.zip'):
                        tqdm.write(f"Deleting .zip file: {file_path}")
                        os.remove(file_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete feature and cache files created or modified today.")
    parser.add_argument('-f','--h5_path', type=str, help='Path to search for .h5 files',
                        default="/data/horse/ws/s1787956-TCGA/features/features-30x")
    parser.add_argument('-c','--zip_path', type=str, help='Path to search for .zip files',
                        default="/data/horse/ws/s1787956-TCGA/Cache/Cache-30x")
    args = parser.parse_args()
    delete_files(args.h5_path, args.zip_path)
