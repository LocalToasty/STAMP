import os
import subprocess
from tqdm import tqdm
import tarfile


# Path to the directory containing the broken files
broken_files_dir = (
    "/data/horse/ws/s1787956-cobra-horse/code/stamp/jobs/scripts/broken.txt"
)

# Read the list of broken files
with open(broken_files_dir, "r") as file:
    broken_files = file.readlines()

archives_dir = "/data/horse/ws/s1787956-TCGA/features-tars"

# Remove empty h5 files and resubmit jobs
for broken_file in tqdm(list(set(broken_files))):
    broken_file = broken_file.strip()

    parts = broken_file.split("/")
    model = parts[7]
    cohort = parts[8].split("-")[-1]

    # Resubmit the job
    # Extract magnification from the file path
    magnification = broken_file.split("/")[6].split("-")[1]

    archive_prefix = f"features-{magnification}_{model}_TCGA-{cohort}"
    # print(f"Searching for archive with prefix: {archive_prefix}")
    for archive in os.listdir(archives_dir):
        if archive_prefix in archive and archive.endswith(".tar"):
            # print(f"Found suitable archive: {archive}")
            archive_path = os.path.join(archives_dir, archive)
            with tarfile.open(archive_path, "r") as tar:
                if os.path.basename(broken_file) in tar.getnames():
                    os.remove(archive_path)
                    print(f"Deleted archive containing broken file: {archive_path}")
                    break

    if os.path.exists(broken_file) and os.path.getsize(broken_file) == 800:
        os.remove(broken_file)
        print(f"Deleted broken file: {broken_file}")

    # submit_command = f'bash submit_jobs.sh "{model}" "{cohort}" 1 1 "{magnification}"'
    # subprocess.run(submit_command, shell=True)
    # print(
    #    f"Resubmitted job for model: {model}, cohort: {cohort}, magnification: {magnification}"
    # )
