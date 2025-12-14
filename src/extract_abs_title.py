import json, os

input_folder = "data/2025json"
output_txt = "data/all_abs_title_topics.txt"

with open(output_txt, "w", encoding="utf-8") as out_f:
    for filename in os.listdir(input_folder):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(input_folder, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            continue  # 文件坏了就跳过

        title = data.get("Title", "No Title")
        abstract = data.get("Abstract", "No Abstract")
        topics = data.get("Topics", "No Topics")

        if isinstance(topics, list):
            topics = "; ".join(topics)

        out_f.write(f"Title: {title}\n")
        out_f.write(f"Abstract: {abstract}\n")
        out_f.write(f"Topics: {topics}\n")
        out_f.write("\n" + "="*80 + "\n\n")

print("Done.")
