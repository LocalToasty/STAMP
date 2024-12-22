#!/bin/bash

# Usage: ./submit_jobs.sh <models> <cohorts> <jobs_per_round> <rounds>
# Example: ./submit_jobs.sh "virchow2 mahmood-uni" "GBM LGG" 3 2

models=($1)
cohorts=($2)
jobs_per_round=$3
rounds=$4

for model in ${models[@]}; do
    for cohort in ${cohorts[@]}; do
        previous_jobs=""
        for round in $(seq 1 $rounds); do
            current_jobs=""
            for job_num in $(seq 1 $jobs_per_round); do
                job_file="../tcga/job_${model}_${cohort}.sh"
                if [ -z "$previous_jobs" ]; then
                    job_id=$(sbatch $job_file | awk '{print $4}')
                else
                    job_id=$(sbatch --dependency=afterany:$previous_jobs $job_file | awk '{print $4}')
                fi
                current_jobs="$current_jobs:$job_id"
            done
            previous_jobs=${current_jobs#:}
        done
    done
done