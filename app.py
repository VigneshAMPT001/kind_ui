# app.py
import json
from pathlib import Path
import pandas as pd
import streamlit as st

# -----------------------
# Config / Data paths
# -----------------------
BASE = Path(".")
NORMALIZED_FILE = BASE / "normalized_all_products.json"
METADATA_SUMMARY_FILE = BASE / "normalized_metadata_summary.json"
CATEGORY_BINS_FILE = BASE / "category_bins.json"

# -----------------------
# Helpers
# -----------------------
def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def format_price(p):
    try:
        return f"${float(p):.2f}"
    except:
        return "-"


# -----------------------
# THEME & UI DESIGN (PREMIUM)
# -----------------------
st.set_page_config(page_title="KIND Marketplace Dashboard", layout="wide")

PRIMARY = "#0057b8"
ACCENT = "#ffd400"

st.markdown(
    f"""
    <style>

    body {{
        background-color: #f7f9fc;
    }}

    /* KPI Card */
    .metric-card {{
        border-radius: 14px;
        padding: 22px;
        background: white;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .kpi {{
        font-size: 32px;
        font-weight: 700;
        color: {PRIMARY};
        margin-bottom: 4px;
    }}
    .kpi-sub {{
        font-size: 14px;
        opacity: 0.8;
    }}

    /* Product Expander */
    .streamlit-expanderHeader {{
        font-size: 18px !important;
        font-weight: 600 !important;
        color: {PRIMARY} !important;
        background-color: #f0f7ff !important;
        border-radius: 8px;
        padding: 10px !important;
    }}

    /* Table styling */
    .dataframe tbody tr:hover {{
        background-color: #f0f4ff;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Load Data
# -----------------------
data_families = load_json(NORMALIZED_FILE) or []
meta = load_json(METADATA_SUMMARY_FILE) or {}
bins = load_json(CATEGORY_BINS_FILE) or {}

# Total products from category_bins.json
total_products = bins.get("total_products", 0)

# -----------------------
# Flatten ASIN-level list + COUNT SKUs + SELLERS
# -----------------------
flat_products = []
total_skus = 0
non_amazon_kind_sellers_set = set()

for fam in data_families:
    product_name = fam.get("product_name") or "Unknown"
    category = fam.get("category") or "Unknown"

    for v in fam.get("variants", []):
        asin = v.get("asin")
        total_skus += 1

        flavor = v.get("variant_name") or v.get("flavor")
        title = v.get("title") or flavor or asin

        # Main seller
        ms = next((s for s in fam.get("main_seller", []) if s.get("asin") == asin), None)

        # Marketplace sellers
        marketplace = [s for s in fam.get("seller_market", []) if s.get("asin") == asin]

        # Track non-Amazon/KIND sellers
        for s in ([ms] if ms else []) + marketplace:
            if not s or not s.get("seller_name"):
                continue
            name = s["seller_name"].lower()
            if name not in ["amazon.com", "kind", "kind snacks"]:
                non_amazon_kind_sellers_set.add(s["seller_name"])

        flat_products.append({
            "asin": asin,
            "product_name": product_name,
            "category": category,
            "title": title,
            "flavor": flavor,
            "size": v.get("size"),
            "price": v.get("price"),
            "unit_price": v.get("unit_price"),
            "prime": v.get("prime"),
            "main_seller": ms,
            "seller_market": marketplace,
            "final_url": v.get("final_url")
        })

non_amazon_kind_sellers = len(non_amazon_kind_sellers_set)

# -----------------------
# PAGE TITLE
# -----------------------
st.markdown(
    f"<h1 style='text-align:center; font-weight:800; color:{PRIMARY}; margin-top:-20px;'>KIND Marketplace Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown("---")

# -----------------------
# KPI CARDS (Clean & Aesthetic)
# -----------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='metric-card'><div class='kpi'>{total_products}</div><div class='kpi-sub'>Total Products</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><div class='kpi'>{total_skus}</div><div class='kpi-sub'>Total SKUs</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><div class='kpi'>{non_amazon_kind_sellers}</div><div class='kpi-sub'>Non-Amazon/KIND Sellers</div></div>", unsafe_allow_html=True)

st.markdown("---")

# -----------------------
# CATEGORY + SELLERS TABLES SIDE-BY-SIDE
# -----------------------
st.markdown("## 📊 Marketplace Summary")

colA, colB = st.columns(2)

# Left Table — SKUs Per Category
with colA:
    st.markdown("### 📦 SKUs Per Category")

    # safe-read the sku mapping from metadata
    sku_dict = meta.get("skus_per_category") or {}

    if sku_dict:
        # build dataframe reliably from dict items, sort ascending, reset index to show 1..N
        df_sku = (
            pd.DataFrame(list(sku_dict.items()), columns=["category", "sku_count"])
              .sort_values(["sku_count", "category"], ascending=[True, True])  # asc by count, then category
              .reset_index(drop=True)
        )

        # make a 1-based serial column / index for nicer display
        df_sku.index = df_sku.index + 1
        df_sku.index.name = "S.No"

        st.dataframe(df_sku, use_container_width=True, height=420)
    else:
        st.info("No SKU-per-category data available in metadata.")

# Right Table — Sellers
with colB:
    st.markdown("### 🛒 Sellers (Excluding Amazon/KIND)")

    sellers = meta.get("unique_sellers_excluding_amazon_and_kind", [])
    if sellers:
        df_sellers = pd.DataFrame({"seller_name": sorted(sellers)})
        st.dataframe(df_sellers, use_container_width=True, height=420)

st.markdown("---")

# -----------------------
# Sidebar (filters)
# -----------------------
st.sidebar.header("Filters")
categories = sorted({p["category"] for p in flat_products})
categories.insert(0, "All Categories")

selected_category = st.sidebar.selectbox("Category", categories)
search_q = st.sidebar.text_input("Search", "")

# -----------------------
# Filtering
# -----------------------
def match(p):
    if selected_category != "All Categories" and p["category"] != selected_category:
        return False

    if search_q.strip() == "":
        return True

    q = search_q.lower()
    return (
        q in p["asin"].lower()
        or q in (p["title"] or "").lower()
        or q in (p["flavor"] or "").lower()
        or q in (p["product_name"] or "").lower()
    )

filtered = [p for p in flat_products if match(p)]

# -----------------------
# PRODUCT LIST HEADER
# -----------------------
st.markdown("## 🛍️ Products")
st.markdown(f"<p style='font-size:18px; color:#444;'>Showing <b>{len(filtered)}</b> SKUs</p>", unsafe_allow_html=True)

# -----------------------
# ACCORDION FOR PRODUCTS
# -----------------------
for p in filtered:
    header = f"{p['product_name']} — {p['flavor']} (ASIN: {p['asin']})"

    with st.expander(header):

        # ------------------------------
        # PRODUCT DETAILS TABLE
        # ------------------------------
        st.markdown("### Product Details")
        st.dataframe(pd.DataFrame([{
            "asin": p["asin"],
            "title": p["title"],
            "price": format_price(p["price"]),
            "unit_price": format_price(p["unit_price"]),
            "prime": "Yes" if p["prime"] else "No",
            "flavor": p["flavor"],
            "size": p["size"],
            "amazon_url": p["final_url"]
        }]), use_container_width=True)

        # ------------------------------
        # MAIN SELLER TABLE
        # ------------------------------
        if p["main_seller"]:
            st.markdown("### Main Seller")
            ms = p["main_seller"]
            st.dataframe(pd.DataFrame([{
                "seller_name": ms.get("seller_name"),
                "ships_from": ms.get("ships_from"),
                "authorized": "Yes" if ms.get("is_authorized") else "No",
                "price": format_price(ms.get("price")),
                "unit_price": format_price(ms.get("unit_price")),
                "prime": "Yes" if ms.get("prime") else "No"
            }]), use_container_width=True)

        # ------------------------------
        # MARKETPLACE SELLERS TABLE
        # ------------------------------
        if p["seller_market"]:
            st.markdown("### Marketplace Sellers")

            sellers_table = []
            for s in p["seller_market"]:

                # ⭐ Gold star rating → 4.5 = ⭐⭐⭐⭐½
                stars_raw = s.get("rating_stars")
                if stars_raw is None:
                    stars_display = "-"
                else:
                    full = int(stars_raw)
                    half = (stars_raw - full) >= 0.5
                    stars_display = "⭐" * full + ("½" if half else "")

                # 🎨 Friendly Price Flag Labels
                pf = s.get("price_flag")
                if pf == "Fair Price":
                    pf_display = "Fair Price (🟢)"
                elif pf == "Slightly High":
                    pf_display = "Slightly High (🟠)"
                elif pf == "High Price":
                    pf_display = "High Price (🟧)"
                elif pf == "Price Gouging":
                    pf_display = "Price Gouging (🔴)"
                else:
                    pf_display = pf or "-"

                sellers_table.append({
                    "seller_name": s.get("seller_name"),
                    "ships_from": s.get("ships_from"),
                    "authorized": "Yes" if s.get("is_authorized") else "No",
                    "price": format_price(s.get("price")),
                    "unit_price": format_price(s.get("unit_price")),
                    "price_delta": (
                        f"${s['price_delta_abs']:.2f}"
                        if s.get("price_delta_abs") is not None else "-"
                    ),
                    "price_flag": pf_display,      # updated label with emojis
                    "rating_stars": stars_display,  # ⭐ updated gold stars
                    "rating_count": s.get("rating_count"),
                    "positive_rating_percent": s.get("positive_rating_percent")
                })

            st.dataframe(pd.DataFrame(sellers_table).fillna("-"), use_container_width=True)

        else:
            st.info("No marketplace sellers found.")

st.markdown("---")
st.caption("Built with normalized KIND marketplace data — Styled with a premium UI 🌟")
