import os
import json

BASE_DIR = "all_products_3"
OUTPUT_FILE = "all_products_merged.json"

def normalize_json():
    merged = {}
    category_order = []

    # Collect categories and ensure All_Snacks comes LAST
    for c in os.listdir(BASE_DIR):
        if c == "All_Snacks":
            continue
        category_order.append(c)

    # Append All_Snacks at the end
    if "All_Snacks" in os.listdir(BASE_DIR):
        category_order.append("All_Snacks")

    print("\nProcessing categories in order:")
    print(category_order)

    for category in category_order:
        path = os.path.join(BASE_DIR, category, "results.json")
        if not os.path.exists(path):
            continue

        print(f"Processing: {path}")

        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        for item in items:
            asin = item.get("asin")
            if not asin:
                continue

            # Add category
            item["category"] = category

            # RULE:
            # ✔ If ASIN already exists, do NOT override (keep real category first)
            if asin not in merged:
                merged[asin] = item

    # Save merged unique items
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(list(merged.values()), out, indent=2, ensure_ascii=False)

    print("\n🎉 Finished Normalizing!")
    print("Unique ASINs:", len(merged))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    normalize_json()
