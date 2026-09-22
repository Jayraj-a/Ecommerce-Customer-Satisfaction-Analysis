"""
data_processing.py
==================
Data loading, cleaning, and merging functions for the E-Commerce Customer
Satisfaction & Delivery Performance Analysis project.

Two analytical DataFrames are produced:

  df_orders — order-level (one row per delivered order)
      Used for: delivery KPIs, customer satisfaction, state analysis,
      time-based trend analysis.

  df_items  — item/category-level (one row per delivered order-item)
      Used for: product category analysis only.
      Prevents double-counting in the main order-level KPIs.

Duplicate review handling rule:
  Where an order has multiple reviews, the LATEST review is kept
  (sort review_creation_date descending, keep first per order_id).

Outlier handling rule:
  - Rows where delivery_time_days < 0 are dropped (physically impossible).
  - Rows where delivery_time_days > 365 are inspected and reported but NOT
    automatically dropped unless delivery_time_days < 0 also applies.
"""

import os
import sys

import pandas as pd

# Force UTF-8 output so diagnostic print statements work on all platforms
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

FILES = {
    "orders":      "olist_orders_dataset.csv",
    "customers":   "olist_customers_dataset.csv",
    "items":       "olist_order_items_dataset.csv",
    "reviews":     "olist_order_reviews_dataset.csv",
    "products":    "olist_products_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

# Datetime columns in each file
DATETIME_COLS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "items": [
        "shipping_limit_date",
    ],
}


# ---------------------------------------------------------------------------
# load_data()
# ---------------------------------------------------------------------------

def load_data() -> dict[str, pd.DataFrame]:
    """
    Load all six CSV files from the data/ directory.

    Returns a dict with keys: orders, customers, items, reviews, products,
    translation.  All datetime columns are parsed immediately.
    """
    raw: dict[str, pd.DataFrame] = {}

    for key, filename in FILES.items():
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path, encoding="utf-8", low_memory=False)

        # Parse datetime columns
        for col in DATETIME_COLS.get(key, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        raw[key] = df

    # -----------------------------------------------------------------------
    # Deduplicate reviews — keep the LATEST review per order_id.
    # Some orders received more than one review; the latest is most
    # representative of the customer's final sentiment.
    # -----------------------------------------------------------------------
    reviews = raw["reviews"]
    reviews_dedup = (
        reviews
        .sort_values("review_creation_date", ascending=False)
        .drop_duplicates(subset="order_id", keep="first")
        .reset_index(drop=True)
    )
    raw["reviews_dedup"] = reviews_dedup

    _print_data_summary(raw)
    return raw


# ---------------------------------------------------------------------------
# _print_data_summary()  — console diagnostics (not shown in dashboard)
# ---------------------------------------------------------------------------

def _print_data_summary(raw: dict[str, pd.DataFrame]) -> None:
    """Print shape and missing-value counts for each loaded DataFrame."""
    print("\n=== Dataset Summary ===")
    for key, df in raw.items():
        if key == "reviews_dedup":
            continue
        nulls = df.isnull().sum()
        cols_with_nulls = nulls[nulls > 0]
        print(f"\n{key}: {df.shape[0]:,} rows × {df.shape[1]} cols")
        if len(cols_with_nulls):
            for col, n in cols_with_nulls.items():
                print(f"  NULL {col}: {n:,}")
        else:
            print("  (no nulls)")

    reviews = raw["reviews"]
    reviews_dedup = raw["reviews_dedup"]
    dup_count = len(reviews) - len(reviews_dedup)
    print(f"\nReviews: {len(reviews):,} total | {dup_count:,} duplicate rows "
          f"removed | {len(reviews_dedup):,} unique orders retained")


# ---------------------------------------------------------------------------
# _compute_delivery_features()  — shared helper
# ---------------------------------------------------------------------------

def _compute_delivery_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add delivery-related computed columns to a DataFrame that already contains
    order_purchase_timestamp, order_delivered_customer_date,
    and order_estimated_delivery_date.

    Columns added:
      delivery_time_days      — calendar days from purchase to actual delivery
      estimated_delivery_days — calendar days from purchase to estimated delivery
      delay_days              — actual - estimated (negative = early, positive = late)
      is_delayed              — True when delay_days > 0
      order_month             — YYYY-MM string for time-trend grouping
    """
    df = df.copy()

    df["delivery_time_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days

    df["estimated_delivery_days"] = (
        df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]
    ).dt.days

    df["delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.days

    df["is_delayed"] = df["delay_days"] > 0

    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)

    return df


# ---------------------------------------------------------------------------
# _report_and_drop_invalid()  — outlier inspection
# ---------------------------------------------------------------------------

def _report_and_drop_invalid(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Inspect delivery_time_days for outliers and drop only impossible records.

    Rules:
      - delivery_time_days < 0  → DROPPED  (delivery before purchase — impossible)
      - delivery_time_days > 365 → REPORTED only; NOT dropped automatically

    Returns cleaned DataFrame.
    """
    total = len(df)

    neg_mask = df["delivery_time_days"] < 0
    neg_count = neg_mask.sum()

    over_365_mask = df["delivery_time_days"] > 365
    over_365_count = over_365_mask.sum()

    print(f"\n=== Outlier Inspection [{label}] ===")
    print(f"  Total rows before outlier check : {total:,}")
    print(f"  delivery_time_days < 0 (invalid): {neg_count:,}  -- DROPPED")
    print(f"  delivery_time_days > 365        : {over_365_count:,}  -- KEPT (flagged only)")

    df = df[~neg_mask].copy()
    print(f"  Rows after dropping invalid     : {len(df):,}")
    return df


# ---------------------------------------------------------------------------
# build_orders_df()
# ---------------------------------------------------------------------------

def build_orders_df(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build the order-level analytical DataFrame (df_orders).

    One row per delivered order. Used for delivery KPIs, customer satisfaction,
    state/location analysis, and time-based trend analysis.

    Join sequence:
      orders (delivered only)
        LEFT JOIN customers   → customer_state, customer_city
        LEFT JOIN reviews     → review_score
        LEFT JOIN items_agg   → total_price, total_freight, item_count
    """
    orders    = raw["orders"]
    customers = raw["customers"]
    reviews   = raw["reviews_dedup"]
    items     = raw["items"]

    # --- 1. Filter to delivered orders only ---
    # Total order count (all statuses) is computed in app.py from raw["orders"]
    delivered = orders[orders["order_status"] == "delivered"].copy()

    # --- 2. Drop rows with missing actual delivery date ---
    delivered = delivered.dropna(subset=["order_delivered_customer_date"])

    # --- 3. Compute delivery features ---
    delivered = _compute_delivery_features(delivered)

    # --- 4. Drop impossible records (delivery_time_days < 0) ---
    delivered = _report_and_drop_invalid(delivered, "df_orders")

    # --- 5. Aggregate order_items to one row per order ---
    items_agg = (
        items
        .groupby("order_id", as_index=False)
        .agg(
            total_price=("price", "sum"),
            total_freight=("freight_value", "sum"),
            item_count=("order_item_id", "count"),
        )
    )

    # --- 6. Join customers ---
    df = delivered.merge(
        customers[["customer_id", "customer_state", "customer_city"]],
        on="customer_id",
        how="left",
    )

    # --- 7. Join reviews ---
    df = df.merge(
        reviews[["order_id", "review_score"]],
        on="order_id",
        how="left",
    )

    # --- 8. Join aggregated items ---
    df = df.merge(items_agg, on="order_id", how="left")

    print(f"\ndf_orders built: {len(df):,} rows × {df.shape[1]} columns")
    print(f"  review_score present: {df['review_score'].notna().sum():,} / {len(df):,}")
    print(f"  is_delayed: {df['is_delayed'].sum():,} delayed, "
          f"{(~df['is_delayed']).sum():,} on-time")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# build_items_df()
# ---------------------------------------------------------------------------

def build_items_df(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build the item/category-level analytical DataFrame (df_items).

    One row per delivered order-item. Used ONLY for product category analysis.
    Allows all relevant product categories to be represented without
    double-counting orders in the main KPIs.

    Join sequence:
      order_items
        LEFT JOIN orders (delivered only) → delivery dates
        LEFT JOIN products                → product_category_name
        LEFT JOIN translation             → product_category_name_english
        LEFT JOIN reviews                 → review_score
    """
    orders      = raw["orders"]
    items       = raw["items"]
    products    = raw["products"]
    translation = raw["translation"]
    reviews     = raw["reviews_dedup"]

    # --- 1. Filter orders to delivered only ---
    delivered_orders = orders[orders["order_status"] == "delivered"][
        [
            "order_id",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]
    ].dropna(subset=["order_delivered_customer_date"])

    # --- 2. Join items → delivered orders ---
    df = items.merge(delivered_orders, on="order_id", how="inner")

    # --- 3. Compute delivery features ---
    df = _compute_delivery_features(df)

    # --- 4. Drop impossible records ---
    df = _report_and_drop_invalid(df, "df_items")

    # --- 5. Join products → category name ---
    products_slim = products[["product_id", "product_category_name"]].copy()
    products_slim["product_category_name"] = (
        products_slim["product_category_name"].fillna("unknown")
    )
    df = df.merge(products_slim, on="product_id", how="left")
    df["product_category_name"] = df["product_category_name"].fillna("unknown")

    # --- 6. Join translation → English category name ---
    df = df.merge(translation, on="product_category_name", how="left")

    # Fallback: if no English translation, use the Portuguese name
    df["product_category_name_english"] = df["product_category_name_english"].where(
        df["product_category_name_english"].notna(),
        df["product_category_name"],
    )

    # --- 7. Join review score ---
    df = df.merge(
        reviews[["order_id", "review_score"]],
        on="order_id",
        how="left",
    )

    print(f"\ndf_items built: {len(df):,} rows × {df.shape[1]} columns")
    print(f"  Unique categories: {df['product_category_name_english'].nunique()}")
    print(f"  review_score present: {df['review_score'].notna().sum():,} / {len(df):,}")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public entry point used by app.py
# ---------------------------------------------------------------------------

def load_and_build() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function called by app.py under @st.cache_data.

    Returns:
        (df_orders, df_items)
    """
    raw = load_data()
    df_orders = build_orders_df(raw)
    df_items  = build_items_df(raw)
    return df_orders, df_items
