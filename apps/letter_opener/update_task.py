import json
import os

review_dir = "data/letter_opener/review"
json_files = sorted([f for f in os.listdir(review_dir) if f.startswith("letter_review_") and f.endswith(".json")])
if not json_files:
    print("No JSON files found.")
    exit(1)

latest_file = os.path.join(review_dir, json_files[-1])
print(f"Updating {latest_file}...")

with open(latest_file, "r", encoding="utf-8") as f:
    data = json.load(f)

for task in data:
    if task.get("task_id") == "LTR-E282":
        task["task_content"] = "供花代支払い"

with open(latest_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Update complete.")
print(latest_file)
