import json
from pathlib import Path
import pandas as pd
import streamlit as st
import math

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
st.set_page_config(
    page_title="KIND Marketplace Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------
# PREMIUM SIDEBAR STYLING (LATEST WORKING VERSION)
# ----------------------------------------------------
sidebar_css = """
<style>

/* Sidebar Background */
[data-testid="stSidebar"] {
    background-color: #f4f6fa !important;
    padding-top: 22px !important;
}

/* Remove the default 'app' title completely */
[data-testid="stSidebar"] [data-testid="stSidebarNav"] > div:nth-child(1),
[data-testid="stSidebarNav"] div[role="heading"] {
    display: none !important;
}

/* Page link styling */
[data-testid="stSidebar"] ul {
    margin-top: 5px !important;
    padding-left: 4px !important;
}

[data-testid="stSidebar"] ul li {
    margin-bottom: 3px !important;
}

[data-testid="stSidebar"] ul li a {
    font-size: 0.96rem !important;
    color: #34495e !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    transition: 0.2s;
    display: block !important;
}

/* Hover effect */
[data-testid="stSidebar"] ul li a:hover {
    background-color: #e6edfa !important;
    color: #003e8c !important;
}

/* Active Page */
[data-testid="stSidebar"] ul li a[data-selected="true"] {
    background-color: #dce6ff !important;
    color: #003e8c !important;
    font-weight: 600 !important;
    border-left: 4px solid #003e8c !important;
    padding-left: 10px !important;
}

</style>
"""
st.markdown(sidebar_css, unsafe_allow_html=True)

# ----------------------------------------------------
# LOAD DATA
# ----------------------------------------------------
BASE = Path(".")
NORMALIZED_FILE = BASE / "normalized_all_products.json"
METADATA_SUMMARY_FILE = BASE / "normalized_metadata_summary.json"
CAPACITY_FILE = BASE / "capacity_bins.json"

def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def load_json_null(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

# Load Data
data_families = load_json(NORMALIZED_FILE) or []
meta = load_json(METADATA_SUMMARY_FILE) or {}
capacity = load_json_null(CAPACITY_FILE) or {}

kind_total_products = capacity.get("total_products", 184)

# Flatten products
flat_products = []
for fam in data_families:
    product_name = fam.get("product_name")
    category = fam.get("category")
    mp_all = fam.get("seller_market", [])
    for v in fam.get("variants", []):
        asin = v.get("asin")
        if not asin:
            continue
        mp = [s for s in mp_all if s.get("asin") == asin]
        flat_products.append({
            "asin": asin,
            "product_name": product_name,
            "category": category,
            "seller_market": mp
        })

# Dashboard Numbers
total_skus = meta.get("total_skus") or len(flat_products)
unique_sellers_excl = sorted(meta.get("unique_sellers_excluding_amazon_and_kind") or [])
sku_per_category = meta.get("skus_per_category") or {}

PRIMARY = "#0057b8"

# ----------------------------------------------------
# HEADER
# ----------------------------------------------------
st.markdown(
    f"""
    <h1 style="text-align:center;color:{PRIMARY};margin-bottom:5px;">
        KIND Marketplace Dashboard
    </h1>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ----------------------------------------------------
# KPI CARDS
# ----------------------------------------------------
kpi_css = """
<style>
.kpi-card {
    background: #ffffff;
    padding: 25px;
    border-radius: 14px;
    text-align: center;
    box-shadow: 0px 3px 12px rgba(0,0,0,0.10);
    border: 1px solid #e3e3e3;
}
.kpi-title {
    font-size: 15px;
    font-weight: 600;
    color: #555;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: #0057b8;
}
</style>
"""
st.markdown(kpi_css, unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

c1.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Total Products (KIND)</div>
    <div class="kpi-value">{kind_total_products}</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Total SKUs</div>
    <div class="kpi-value">{total_skus}</div>
</div>
""", unsafe_allow_html=True)

c3.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Unique Sellers (Excl Amazon & KIND)</div>
    <div class="kpi-value">{len(unique_sellers_excl)}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ----------------------------------------------------
# CATEGORY + SELLER SUMMARY
# ----------------------------------------------------
left, right = st.columns([2,1])

with left:
    st.subheader("📦 SKUs Per Category (ascending)")
    if sku_per_category:
        df_cat = pd.DataFrame(
            list(sku_per_category.items()),
            columns=["category", "sku_count"]
        ).sort_values("sku_count").reset_index(drop=True)
        st.dataframe(df_cat, use_container_width=True)
    else:
        st.info("No category data available.")

with right:
    st.subheader("🛒 Sellers (Excl Amazon/KIND)")
    if unique_sellers_excl:
        st.dataframe(pd.DataFrame({"seller_name": unique_sellers_excl}),
                     use_container_width=True)
    else:
        st.info("No seller list found.")

st.markdown("---")

# ----------------------------------------------------
# ADDITIONAL INSIGHTS
# ----------------------------------------------------
st.header("Additional Insights")

left2, right2 = st.columns(2)

# 👉 Top Gouged SKUs
with left2:
    st.subheader("🔥 Top 10 Most Gouged SKUs")
    gouged = []
    for s in flat_products:
        asin = s["asin"]
        max_pct = None
        worst_seller = None
        for mk in s.get("seller_market") or []:
            pct = mk.get("price_delta_percent")
            if pct is not None and (max_pct is None or pct > max_pct):
                max_pct = pct
                worst_seller = mk.get("seller_name")
        if max_pct is not None:
            gouged.append({
                "asin": asin,
                "product_name": s["product_name"],
                "category": s["category"],
                "max_pct": max_pct,
                "seller": worst_seller
            })

    df_g = pd.DataFrame(sorted(gouged, key=lambda x: x["max_pct"], reverse=True)[:10])
    if not df_g.empty:
        df_g["max_pct"] = df_g["max_pct"].map(lambda x: f"{x:.1f}%")
        st.dataframe(df_g, use_container_width=True)
    else:
        st.info("No gouging detected.")

# 👉 Seller Impact
with right2:
    st.subheader("🏬 Seller SKU Impact")

    impact = {}
    for s in flat_products:
        seen = set()
        for mk in s.get("seller_market") or []:
            nm = mk.get("seller_name")
            if nm:
                seen.add(nm)
        for nm in seen:
            impact[nm] = impact.get(nm, 0) + 1

    df_i = pd.DataFrame(
        [{"seller": k, "sku_count": v} for k, v in impact.items()]
    ).sort_values("sku_count", ascending=False).reset_index(drop=True)

    if not df_i.empty:
        st.dataframe(df_i, use_container_width=True)
    else:
        st.info("No seller impact data.")

st.markdown("---")
st.caption("Dashboard view — Additional insights included. Product list available in Products page.")
