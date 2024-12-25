import os
import argparse

feature_extractors = ["virchow2", "mahmood-uni", "mahmood-conch", "h_optimus_0", "gigapath","dinoSSL","ctranspath"]
cohorts = [
    "GBM", "LGG", "BLCA", "LUAD", "BRCA", "DLBC", "CHOL", "ESCA", "CRC", "CESC", 
    "UCS", "UCEC", "THYM", "THCA", "TGCT", "STAD", "SKCM", "SARC", "PRAD", "PCPG", 
    "PAAD", "OV", "MESO", "LUSC", "LIHC", "KIRP", "KIRC", "KICH", "HNSC"
]

wsi_base_dir = "/data/horse/ws/s1787956-TCGA/WSI"
h5_base_dir = "/data/horse/ws/s1787956-TCGA/features/features-20x"

def count_files(directory, extension):
    return len([f for f in os.listdir(directory) if f.endswith(extension)])

def count_non_empty_h5_files(directory):
    return len([f for f in os.listdir(directory) if f.endswith('.h5') and os.path.getsize(os.path.join(directory, f)) > 0])

def check_preprocessing():
    for cohort in cohorts:
        wsi_dir = os.path.join(wsi_base_dir, f"TCGA-{cohort}-DX-IMGS",f"data-{cohort}")
        num_wsi_files = count_files(wsi_dir, '.svs')
        
        for model in feature_extractors:
            model_dir = os.path.join(h5_base_dir, model, f"TCGA-{cohort}")
            if os.path.exists(model_dir):
                subdirs = [d for d in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, d)) and model in d]
                if subdirs:
                    h5_dir = os.path.join(model_dir, subdirs[0])
                else:
                    continue
                if os.path.exists(h5_dir):
                    num_h5_files = count_non_empty_h5_files(h5_dir)
                else:
                    continue            
                if num_h5_files == num_wsi_files:
                    print(f"Cohort {cohort} is completely processed for model {model} with {num_wsi_files} WSIs")
                elif num_h5_files > 0:
                    print(f"Cohort {cohort} is partially processed for model {model}: {num_h5_files}/{num_wsi_files} slides processed")
            else:
                continue
def get_missing_wsi_files(wsi_dir, h5_dir):
    wsi_files = {f for f in os.listdir(wsi_dir) if f.endswith('.svs')}
    h5_files = {f.replace('.h5', '.svs') for f in os.listdir(h5_dir) if f.endswith('.h5') and os.path.getsize(os.path.join(h5_dir, f)) > 0}
    missing_files = wsi_files - h5_files
    return [os.path.join(wsi_dir, f) for f in missing_files]
    wsi_files = {f for f in os.listdir(wsi_dir) if f.endswith('.svs')}
    h5_files = {f.replace('.h5', '.svs') for f in os.listdir(h5_dir) if f.endswith('.h5') and os.path.getsize(os.path.join(h5_dir, f)) > 0}
    missing_files = wsi_files - h5_files
    return [os.path.join(wsi_dir, f) for f in missing_files]

def print_missing_wsi_files(print_cohorts,print_feat_exts):
    for cohort in print_cohorts:
        wsi_dir = os.path.join(wsi_base_dir, f"TCGA-{cohort}-DX-IMGS", f"data-{cohort}")
        for model in feature_extractors:
            model_dir = os.path.join(h5_base_dir, model, f"TCGA-{cohort}")
            if os.path.exists(model_dir):
                subdirs = [d for d in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, d)) and model in d]
                if subdirs:
                    h5_dir = os.path.join(model_dir, subdirs[0])
                else:
                    continue
                if os.path.exists(h5_dir):
                    missing_files = get_missing_wsi_files(wsi_dir, h5_dir)
                    for file in missing_files:
                        print(file)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check preprocessing status of WSIs")
    parser.add_argument('--print-missing', action='store_true', help="Print missing WSIs")
    parser.add_argument('--cohorts', nargs='+', default=cohorts, help="List of cohorts to check, e.g., --cohorts GBM LGG BLCA")
    parser.add_argument('--models', nargs='+', default=feature_extractors, help="List of models to check, e.g., --models virchow2 mahmood-uni")
    args = parser.parse_args()
    if args.print_missing:
        print_missing_wsi_files(args.cohorts,args.models)
    check_preprocessing()
