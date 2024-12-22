import os
import yaml
from tqdm import tqdm 

# Define the base configuration
base_config = {
    'preprocessing': {
        'output_dir': "",
        'wsi_dir': "",
        'extractor': "",
        'accelerator': "cuda",
        'cache_dir': "",
        'tile_size_um': 112.0,
        'tile_size_px': 224,
        'max_workers': 14
    }
}

# Define the different feature extractors and cohorts
feature_extractors = ["virchow2","mahmood-uni", "mahmood-conch","h-optimus-0","gigapath"] # google model is tf so would avoid.. 
cohorts = [
    "GBM", "LGG", "BLCA", "LUAD", "BRCA", "DLBC", "CHOL", "ESCA", "CRC", "CESC", 
    "UCS", "UCEC", "THYM", "THCA", "TGCT", "STAD", "SKCM", "SARC", "PRAD", "PCPG", 
    "PAAD", "OV", "MESO", "LUSC", "LIHC", "KIRP", "KIRC", "KICH", "HNSC"
]

# Define the directories
base_output_dir = "/data/horse/ws/s1787956-TCGA/features/features-20x"
base_wsi_dir = "/data/horse/ws/s1787956-TCGA/WSI"
base_cache_dir = "/data/horse/ws/s1787956-TCGA/Cache/Cache-20x"
config_dir = "/data/horse/ws/s1787956-cobra-horse/code/stamp/src/stamp/configs"
job_dir = "/data/horse/ws/s1787956-cobra-horse/code/stamp/jobs/tcga"

# Create directories if they don't exist
os.makedirs(config_dir, exist_ok=True)
os.makedirs(job_dir, exist_ok=True)

# Generate config files and job scripts
for extractor in tqdm(feature_extractors):
    for cohort in tqdm(cohorts,leave=False):
        config = base_config.copy()
        config['preprocessing']['output_dir'] = f"{base_output_dir}/{extractor}/TCGA-{cohort}"
        config['preprocessing']['wsi_dir'] = f"{base_wsi_dir}/TCGA-{cohort}-DX-IMGS/data-{cohort}"
        config['preprocessing']['extractor'] = extractor
        config['preprocessing']['cache_dir'] = f"{base_cache_dir}/TCGA-{cohort}"

        config_filename = f"{config_dir}/config_{extractor}_{cohort}.yaml"
        job_filename = f"{job_dir}/job_{extractor}_{cohort}.sh"

        # Save the config file
        with open(config_filename, 'w') as config_file:
            yaml.dump(config, config_file)

        # Create the job script
        job_script = f"""#!/bin/bash
#SBATCH --job-name=preprocess-{extractor}-{cohort}
#SBATCH --output="outs/stamp_preprocess_{extractor}_{cohort}_%j.out"
#SBATCH --mail-type=END
#SBATCH --mail-user=tim.lenz@tu-dresden.de
#SBATCH --ntasks=1
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=14
#SBATCH --mem=128G
#SBATCH --time=8:00:00
#SBATCH --account=p_scads_pathology
#SBATCH --partition=capella

# Load any necessary modules
# module load CUDA

# Your job commands go here
cd /data/horse/ws/s1787956-cobra-horse/code/stamp
export XDG_CACHE_HOME="/data/horse/ws/s1787956-Cache"
stamp -c {config_filename} preprocess
"""

        # Save the job script
        with open(job_filename, 'w') as job_file:
            job_file.write(job_script)