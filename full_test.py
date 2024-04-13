import os
import requests
import json
import time


def process_files_in_folder(folder_path, results={}):

    api_key = os.environ.get("API_KEY")  # Retrieve API key from environment variable
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".mp3") or file.endswith(".wav"):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start=folder_path)
                if (
                    results.get(folder_path, {})
                    .get(relative_path, {})
                    .get("job_completed")
                ):
                    print(f"Job for {relative_path} already completed.")
                    continue
                with open(file_path, "rb") as f:
                    print(f"Launching job for {file_path}")
                    files = {"file": (file, f, "audio/mpeg")}
                    response = requests.post(
                        "https://api.deeptrustai.com/api/job",
                        headers=headers,
                        files=files,
                    )
                    if response.status_code == 200:
                        job_id = response.json().get("job_id")
                        # Update results with a structure organized by voice type and then file name
                        if folder_path not in results:
                            results[folder_path] = {}
                        results[folder_path][relative_path] = {"job_id": job_id}
                        print(f"Launched 🚀")
                    else:
                        print(f"Error processing file {file_path}: {response.text}")

    return results


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


def load_test_results():
    try:
        with open("test_results.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("File not found.")
        return None


def calculate_eer(test_results):
    ai_scores = [
        details["results"]["score"]
        for details in test_results.get("ai_voices", {}).values()
        if "results" in details
    ]
    real_scores = [
        details["results"]["score"]
        for details in test_results.get("real_voices", {}).values()
        if "results" in details
    ]

    # Combining scores to find potential thresholds
    combined_scores = sorted(set(ai_scores + real_scores))

    def calculate_far_frr(threshold):
        far = (
            sum(score <= threshold for score in ai_scores) / len(ai_scores)
            if ai_scores
            else 0
        )
        frr = (
            sum(score > threshold for score in real_scores) / len(real_scores)
            if real_scores
            else 0
        )
        return far, frr

    eer = 1
    eer_threshold = None
    for threshold in combined_scores:
        far, frr = calculate_far_frr(threshold)
        # Looking for the point where FAR is closest to FRR
        if abs(far - frr) < abs(eer - (far + frr) / 2):
            eer = (far + frr) / 2
            eer_threshold = threshold

    return eer, eer_threshold


if __name__ == "__main__":
    # Initialize or load existing results
    if os.path.exists("test_results.json"):
        with open("test_results.json", "r") as file:
            test_results = json.load(file)
    else:
        test_results = {}

    # Process files in specified folders
    voice_types = ["ai_voices", "real_voices"]
    for voice_type in voice_types:
        folder_results = process_files_in_folder(voice_type, test_results)
        test_results.update(folder_results)

    # Store the updated results in "test_results.json"
    with open("test_results.json", "w") as file:
        json.dump(test_results, file, indent=4)

    print("Processing complete. Results stored in 'test_results.json'.")

    update_results_with_polling()

    # Load the test results and calculate EER
    test_results = load_test_results()
    if test_results:
        eer, eer_threshold = calculate_eer(test_results)
        print(f"Estimated EER: {eer:.4f} at threshold: {eer_threshold}")
    else:
        print("Unable to calculate EER.")
