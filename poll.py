import os
import requests
import json
import time


def poll_job_status(job_id, api_key, max_retries=1, timeout=300):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    url = f"https://api.deeptrustai.com/api/job/poll/{job_id}"
    retries = 0
    start_time = time.time()

    print(f"Starting to poll for job ID: {job_id}")
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"Polling successful for job ID: {job_id}")
            return response.json(), True
        elif retries >= max_retries:
            print(f"Max retries reached for job ID: {job_id}. Moving to the next job.")
            return None, False
        retries += 1
        print(f"Retrying... (Attempt {retries + 1} for job ID: {job_id})")
        time.sleep(10)  # Wait for 10 seconds before retrying

    print(f"Timeout reached for job ID: {job_id}. Moving to the next job.")
    return None, False


def update_results_with_polling():
    api_key = os.environ.get(
        "API_KEY"
    )  # Ensure API_KEY is set as an environment variable
    if not api_key:
        print("API_KEY environment variable not set.")
        return

    if not os.path.exists("test_results.json"):
        print("test_results.json file does not exist.")
        return

    with open("test_results.json", "r") as file:
        test_results = json.load(file)

    for voice_type, files in test_results.items():
        print(f"Processing {voice_type}...")
        for file_name, job_info in files.items():
            job_id = job_info.get("job_id")
            if (
                job_id and "results" not in job_info
            ):  # Check if job has not been polled yet
                print(f"Polling job for file: {file_name}")
                result, job_completed = poll_job_status(job_id, api_key)
                if result is not None:
                    test_results[voice_type][file_name]["results"] = result
                    test_results[voice_type][file_name]["job_completed"] = job_completed
                    print(f"Polling result stored for file: {file_name}")
                else:
                    test_results[voice_type][file_name]["job_completed"] = False
                    print(f"Failed to complete polling for file: {file_name}")

    with open("test_results.json", "w") as file:
        json.dump(test_results, file, indent=4)

    print("Polling complete. Results updated in 'test_results.json'.")


update_results_with_polling()
