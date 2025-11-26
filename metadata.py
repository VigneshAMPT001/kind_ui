import os
import json

BASE_DIR = "kind_products_final"
OUTPUT_FILE = "kind_products_metadata.json"


def generate_metadata():
    output = {
        "total_categories": 0,
        "total_products": 0,
        "products_available_on_amazon": 0,
        "products_missing_on_amazon": 0,
        "availability_percent_overall": 0,
        "category_breakdown": []
    }

    # loop through category folders
    for category in os.listdir(BASE_DIR):
        category_path = os.path.join(BASE_DIR, category)

        if not os.path.isdir(category_path):
            continue

        results_file = os.path.join(category_path, "results.json")
        if not os.path.exists(results_file):
            continue

        with open(results_file, "r") as f:
            items = json.load(f)

        total = len(items)
        available = sum(
            1 for p in items
            if p.get("amazon_link") and p["amazon_link"].get("amazon")
        )
        missing = total - available

        cat_display = category.replace("_", " ").title()

        output["category_breakdown"].append({
            "category": category,
            "category_display": cat_display,
            "total_products": total,
            "available_on_amazon": available,
            "missing_on_amazon": missing,
            "availability_percent": round((available / total) * 100, 2) if total else 0
        })

        # global counters
        output["total_categories"] += 1
        output["total_products"] += total
        output["products_available_on_amazon"] += available
        output["products_missing_on_amazon"] += missing

    # compute overall %
    if output["total_products"] > 0:
        output["availability_percent_overall"] = round(
            (output["products_available_on_amazon"] / output["total_products"]) * 100,
            2
        )

    # write output json
    with open(OUTPUT_FILE, "w") as out:
        json.dump(output, out, indent=4)

    print("✔ Metadata created:", OUTPUT_FILE)
    print("✔ Total categories:", output["total_categories"])
    print("✔ Total products:", output["total_products"])
    print("✔ Available on Amazon:", output["products_available_on_amazon"])


if __name__ == "__main__":
    generate_metadata()
