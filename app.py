import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# Page setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Amazon Category Dashboard",
    page_icon="📦",
    layout="wide",
)

# Small amount of custom styling to make the dashboard cleaner
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetric"] {
            background: rgba(127, 127, 127, 0.06);
            border: 1px solid rgba(127, 127, 127, 0.18);
            padding: 14px 16px;
            border-radius: 14px;
        }
        div[data-testid="stMetric"] label {
            font-size: 0.85rem;
        }
        .dashboard-subtitle {
            color: #6b7280;
            margin-top: -0.4rem;
            margin-bottom: 1.2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Data loading and cleaning
# ---------------------------------------------------------
@st.cache_data
def load_and_clean_data(file_or_path):
    """Load the raw Amazon CSV and apply the same basic cleaning used in the notebook."""

    # Read either an uploaded file or a local CSV path
    df = pd.read_csv(file_or_path)

    # Remove currency symbols and commas, then convert prices to numeric values
    for column in ["discounted_price", "actual_price"]:
        df[column] = (
            df[column]
            .astype(str)
            .str.replace("₹", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Convert discount percentage from strings such as '64%' to decimal values such as 0.64
    df["discount_percentage"] = (
        df["discount_percentage"]
        .astype(str)
        .str.replace("%", "", regex=False)
    )
    df["discount_percentage"] = pd.to_numeric(
        df["discount_percentage"], errors="coerce"
    ) / 100

    # Convert rating and rating_count to numeric values
    # Invalid values such as '|' in rating become NaN
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_count"] = (
        df["rating_count"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce")

    # Remove rows where the target rating or popularity count is missing
    df = df.dropna(subset=["rating", "rating_count"]).copy()

    # Keep one row per product ID, preferring the row with the highest rating_count
    df = df.sort_values("rating_count", ascending=False)
    df = df.drop_duplicates(subset="product_id", keep="first").copy()

    # Extract the first and second levels from the Amazon category path
    category_parts = df["category"].astype(str).str.split("|")
    df["main_category"] = category_parts.str[0]
    df["sub_category"] = category_parts.str[1].fillna("Other")

    # Extra display-friendly percentage column for Plotly and tables
    df["discount_pct"] = df["discount_percentage"] * 100

    return df.reset_index(drop=True)


# Load the bundled dataset; fall back to upload if it is unavailable.
local_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amazon.csv")

if os.path.exists(local_csv):
    data_source = local_csv
else:
    data_source = st.sidebar.file_uploader(
        "Upload amazon.csv",
        type=["csv"],
        help="Upload the Amazon dataset used in the assignment.",
    )

if data_source is None:
    st.title("Amazon Category Performance Dashboard")
    st.info("Upload amazon.csv from the sidebar to open the dashboard.")
    st.stop()

try:
    df = load_and_clean_data(data_source)
except Exception as error:
    st.error(f"The dataset could not be loaded: {error}")
    st.stop()


# ---------------------------------------------------------
# Dashboard header
# ---------------------------------------------------------
st.title("Amazon Category Performance Dashboard")
st.markdown(
    '<div class="dashboard-subtitle">Interactive category-level view of ratings, pricing, discounts and popularity.</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------
st.sidebar.header("Dashboard filters")

all_categories = sorted(df["main_category"].dropna().unique().tolist())

selected_categories = st.sidebar.multiselect(
    "Main categories",
    options=all_categories,
    default=all_categories,
    help="Select one or more categories to include in the dashboard.",
)

if not selected_categories:
    st.warning("Select at least one category from the sidebar.")
    st.stop()

filtered_df = df[df["main_category"].isin(selected_categories)].copy()

# Build category-level metrics used by all charts and tables
category_summary = (
    filtered_df.groupby("main_category", as_index=False)
    .agg(
        product_count=("product_id", "nunique"),
        mean_rating=("rating", "mean"),
        median_rating=("rating", "median"),
        median_discount_pct=("discount_pct", "median"),
        median_actual_price=("actual_price", "median"),
        median_discounted_price=("discounted_price", "median"),
        total_rating_count=("rating_count", "sum"),
        median_rating_count=("rating_count", "median"),
    )
)

max_products_in_category = int(category_summary["product_count"].max())
min_products = st.sidebar.slider(
    "Minimum products in category",
    min_value=1,
    max_value=max_products_in_category,
    value=1,
    help="Use this to hide categories with very small sample sizes.",
)

category_summary = category_summary[
    category_summary["product_count"] >= min_products
].copy()

if category_summary.empty:
    st.warning("No categories match the current minimum-product filter.")
    st.stop()

metric_options = {
    "Average rating": "mean_rating",
    "Product count": "product_count",
    "Median discount (%)": "median_discount_pct",
    "Median actual price (₹)": "median_actual_price",
    "Median rating count": "median_rating_count",
}

selected_metric_label = st.sidebar.selectbox(
    "Bar-chart metric",
    options=list(metric_options.keys()),
    index=0,
)
selected_metric = metric_options[selected_metric_label]

sort_direction = st.sidebar.radio(
    "Sort categories",
    options=["Highest first", "Lowest first"],
    horizontal=False,
)
ascending = sort_direction == "Lowest first"


# ---------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric("Products", f"{filtered_df['product_id'].nunique():,}")

with metric_col2:
    st.metric("Average rating", f"{filtered_df['rating'].mean():.2f} / 5")

with metric_col3:
    st.metric("Median discount", f"{filtered_df['discount_pct'].median():.1f}%")

with metric_col4:
    st.metric("Median actual price", f"₹{filtered_df['actual_price'].median():,.0f}")

st.divider()


# ---------------------------------------------------------
# Chart 1: selected category-level metric
# ---------------------------------------------------------
left_col, right_col = st.columns([1.15, 1])

with left_col:
    st.subheader(f"Category comparison — {selected_metric_label}")

    bar_data = category_summary.sort_values(
        selected_metric, ascending=ascending
    ).copy()

    # Format values displayed directly on bars
    if selected_metric == "mean_rating":
        bar_data["display_value"] = bar_data[selected_metric].map(lambda value: f"{value:.2f}")
    elif selected_metric == "median_discount_pct":
        bar_data["display_value"] = bar_data[selected_metric].map(lambda value: f"{value:.1f}%")
    elif selected_metric == "median_actual_price":
        bar_data["display_value"] = bar_data[selected_metric].map(lambda value: f"₹{value:,.0f}")
    else:
        bar_data["display_value"] = bar_data[selected_metric].map(lambda value: f"{value:,.0f}")

    bar_fig = px.bar(
        bar_data,
        x=selected_metric,
        y="main_category",
        orientation="h",
        text="display_value",
        labels={
            "main_category": "Main category",
            selected_metric: selected_metric_label,
        },
        hover_data={
            "product_count": ":,",
            "mean_rating": ":.2f",
            "median_discount_pct": ":.1f",
            "median_actual_price": ":,.0f",
            "display_value": False,
        },
    )

    bar_fig.update_layout(
        height=max(390, 42 * len(bar_data)),
        margin=dict(l=10, r=20, t=10, b=10),
        yaxis_title=None,
    )
    bar_fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(bar_fig, use_container_width=True)


# ---------------------------------------------------------
# Chart 2: rating vs discount relationship by category
# ---------------------------------------------------------
with right_col:
    st.subheader("Rating vs discount by category")

    scatter_fig = px.scatter(
        category_summary,
        x="median_discount_pct",
        y="mean_rating",
        size="product_count",
        color="median_actual_price",
        hover_name="main_category",
        labels={
            "median_discount_pct": "Median discount (%)",
            "mean_rating": "Average rating",
            "product_count": "Products",
            "median_actual_price": "Median price (₹)",
        },
        hover_data={
            "product_count": ":,",
            "median_actual_price": ":,.0f",
            "median_rating_count": ":,.0f",
        },
        size_max=52,
    )

    scatter_fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_colorbar=dict(title="Median<br>price (₹)"),
    )
    st.plotly_chart(scatter_fig, use_container_width=True)

st.caption(
    "Bubble size represents the number of products in each category. Categories with very few products should be interpreted cautiously."
)

st.divider()


# ---------------------------------------------------------
# Drill-down: inspect one category and its sub-categories
# ---------------------------------------------------------
st.subheader("Explore a category")

detail_category = st.selectbox(
    "Choose a main category",
    options=category_summary.sort_values("product_count", ascending=False)[
        "main_category"
    ].tolist(),
)

category_df = filtered_df[filtered_df["main_category"] == detail_category].copy()

sub_summary = (
    category_df.groupby("sub_category", as_index=False)
    .agg(
        product_count=("product_id", "nunique"),
        mean_rating=("rating", "mean"),
        median_discount_pct=("discount_pct", "median"),
        median_actual_price=("actual_price", "median"),
        median_rating_count=("rating_count", "median"),
    )
    .sort_values("product_count", ascending=False)
)

# Keep the sub-category chart readable by showing the 12 largest groups
sub_plot_data = sub_summary.head(12).sort_values("product_count", ascending=True)

sub_left, sub_right = st.columns([1.15, 1])

with sub_left:
    sub_fig = px.bar(
        sub_plot_data,
        x="product_count",
        y="sub_category",
        orientation="h",
        text="product_count",
        labels={
            "product_count": "Number of products",
            "sub_category": "Sub-category",
        },
        hover_data={
            "mean_rating": ":.2f",
            "median_discount_pct": ":.1f",
            "median_actual_price": ":,.0f",
        },
    )
    sub_fig.update_layout(
        height=460,
        margin=dict(l=10, r=20, t=10, b=10),
        yaxis_title=None,
    )
    sub_fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(sub_fig, use_container_width=True)

with sub_right:
    st.markdown(f"#### {detail_category} at a glance")

    detail_metrics_1, detail_metrics_2 = st.columns(2)
    with detail_metrics_1:
        st.metric("Products", f"{category_df['product_id'].nunique():,}")
        st.metric("Median discount", f"{category_df['discount_pct'].median():.1f}%")
    with detail_metrics_2:
        st.metric("Average rating", f"{category_df['rating'].mean():.2f}")
        st.metric("Median price", f"₹{category_df['actual_price'].median():,.0f}")

    st.markdown("**Sub-category metrics**")
    table_data = sub_summary.copy()
    table_data = table_data.rename(
        columns={
            "sub_category": "Sub-category",
            "product_count": "Products",
            "mean_rating": "Avg rating",
            "median_discount_pct": "Median discount (%)",
            "median_actual_price": "Median price (₹)",
            "median_rating_count": "Median rating count",
        }
    )

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Avg rating": st.column_config.NumberColumn(format="%.2f"),
            "Median discount (%)": st.column_config.NumberColumn(format="%.1f"),
            "Median price (₹)": st.column_config.NumberColumn(format="₹ %.0f"),
            "Median rating count": st.column_config.NumberColumn(format="%,.0f"),
        },
    )

st.divider()


# ---------------------------------------------------------
# Full category-level summary table
# ---------------------------------------------------------
with st.expander("View complete category-level metrics table"):
    final_table = category_summary.copy()
    final_table = final_table.rename(
        columns={
            "main_category": "Main category",
            "product_count": "Products",
            "mean_rating": "Average rating",
            "median_rating": "Median rating",
            "median_discount_pct": "Median discount (%)",
            "median_actual_price": "Median actual price (₹)",
            "median_discounted_price": "Median discounted price (₹)",
            "total_rating_count": "Total rating count",
            "median_rating_count": "Median rating count",
        }
    )

    st.dataframe(
        final_table.sort_values("Products", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Average rating": st.column_config.NumberColumn(format="%.2f"),
            "Median rating": st.column_config.NumberColumn(format="%.2f"),
            "Median discount (%)": st.column_config.NumberColumn(format="%.1f"),
            "Median actual price (₹)": st.column_config.NumberColumn(format="₹ %.0f"),
            "Median discounted price (₹)": st.column_config.NumberColumn(format="₹ %.0f"),
            "Total rating count": st.column_config.NumberColumn(format="%,.0f"),
            "Median rating count": st.column_config.NumberColumn(format="%,.0f"),
        },
    )
