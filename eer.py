import json


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


# Load the test results and calculate EER
test_results = load_test_results()
if test_results:
    eer, eer_threshold = calculate_eer(test_results)
    print(f"Estimated EER: {eer:.4f} at threshold: {eer_threshold}")
else:
    print("Unable to calculate EER.")
