import os
import requests
import json


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
