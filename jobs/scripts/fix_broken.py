import os
import subprocess
from tqdm import tqdm

# Path to the directory containing the broken files
broken_files_dir = '/data/horse/ws/s1787956-cobra-horse/code/stamp/jobs/scripts/broken.txt'

# Read the list of broken files
with open(broken_files_dir, 'r') as file:
    broken_files = file.readlines()

archives_dir = '/data/horse/ws/s1787956-TCGA/features-tars'

# Remove empty h5 files and resubmit jobs
for broken_file in tqdm(list(set(broken_files))):
    broken_file = broken_file.strip()
    
    parts = os.path.basename(broken_file).split('_')
    model = parts[1]
    cohort = parts[2].split('.')[0]
    
    # Resubmit the job
    # Extract magnification from the file path
    magnification = broken_file.split('/')[7].split('-')[1]
    
    archive_prefix = f"features-{magnification}_{model}_{cohort}"
    for archive in os.listdir(archives_dir):
        if archive.startswith(archive_prefix) and archive.endswith('.tar'):
            archive_path = os.path.join(archives_dir, archive)
            with tarfile.open(archive_path, 'r') as tar:
                if broken_file in tar.getnames():
                    os.remove(archive_path)
                    print(f"Deleted archive containing broken file: {archive_path}")
                    break
    
    if os.path.exists(broken_file) and os.path.getsize(broken_file) == 800:
        
        os.remove(broken_file)
        print(f"Deleted broken file: {broken_file}")
        
    submit_command = f"./submit_jobs.sh \"{model}\" \"{cohort}\" 1 1 \"{magnification}\""
    subprocess.run(submit_command, shell=True)
    print(f"Resubmitted job for model: {model}, cohort: {cohort}, magnification: {magnification}")