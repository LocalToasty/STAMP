import argparse
import os
import shutil
import glob
from tqdm import tqdm 

def move_slide(slide_names, sorted_out_folder, wsi_folder):
    if not os.path.exists(sorted_out_folder):
        os.makedirs(sorted_out_folder)
    
    for slide_name in slide_names:
        slide_pattern = os.path.join(wsi_folder, '**', f"{slide_name}*.svs")
        slide_files = glob.glob(slide_pattern, recursive=True)
        
        if slide_files:
            slide_path = slide_files[0]
            destination_path = os.path.join(sorted_out_folder, os.path.basename(slide_path))
            shutil.move(slide_path, destination_path)
            print(f"Moved {slide_path} to {destination_path}")
        else:
            print(f"No slide starting with {slide_name} found in {wsi_folder}")

def remove_cache_and_features(slide_names, cache_parent_folder, feature_parent_folder):
    for parent_folder in [cache_parent_folder, feature_parent_folder]:
        for root, dirs, files in tqdm(os.walk(parent_folder), desc=f"Processing {parent_folder}"):
            for file in tqdm(files, desc=f"Processing {root}", leave=False):
                if any(file.startswith(slide_name) for slide_name in slide_names):
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    tqdm.write(f"Removed {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Move slide and remove cache and feature files.")
    parser.add_argument("-s", "--slide_names", nargs='+', help="List of slide names to be moved and cleaned up"
                        , default=["TCGA-19-1389-01Z-00-DX1","TCGA-19-1388-01Z-00-DX1","TCGA-06-1086-01Z-00-DX2",
                                   "TCGA-14-1401-01Z-00-DX1","TCGA-HT-7483-01Z-00-DX1","TCGA-44-7661-01Z-00-DX1"]) 
                        # TCGA-44-7661-01Z-00-DX1 TCGA-HT-7483-01Z-00-DX1
    parser.add_argument("-w", "--wsi_folder", help="Folder containing WSIs", 
                        default="/data/horse/ws/s1787956-TCGA/WSI")
    parser.add_argument("-b", "--sorted_out_folder", help="Folder to move the slide to", 
                        default="/data/horse/ws/s1787956-TCGA/WSI-broken")
    parser.add_argument("-c", "--cache_parent_folder", help="Parent folder for cache files",
                        default="/data/horse/ws/s1787956-TCGA/Cache")
    parser.add_argument("-f", "--feature_parent_folder", help="Parent folder for feature files",
                        default="/data/horse/ws/s1787956-TCGA/features")
    
    args = parser.parse_args()
    
    move_slide(args.slide_names, args.sorted_out_folder, args.wsi_folder)
    remove_cache_and_features(args.slide_names, args.cache_parent_folder, args.feature_parent_folder)

if __name__ == "__main__":
    main()