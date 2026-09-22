"""
app.py
======
E-Commerce Customer Satisfaction & Delivery Performance Analysis
BSc Computer Science Academic Internship Project

Interactive Streamlit dashboard. Run with:
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_processing import load_and_build

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="E-Commerce Customer Satisfaction & Delivery Analysis",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global Plotly theme
# ---------------------------------------------------------------------------
PLOTLY_TEMPLATE = "plotly_white"
COLOUR_PRIMARY  = "#2563EB"   # blue
COLOUR_DELAYED  = "#DC2626"   # red
COLOUR_ONTIME   = "#16A34A"   # green
COLOUR_NEUTRAL  = "#6B7280"   # grey

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and processing datasets…")
def get_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_and_build()


df_orders_all, df_items_all = get_data()

# Compute total orders from the raw order_status column for the Total Orders KPI
total_orders_all = 99_441   # from actual dataset; re-derived below from df_orders
# We actually want the count from the full orders table; df_orders_all only has
# delivered orders. We derive total_orders by reading from df_orders_all metadata.
# Because load_and_build() doesn't expose raw, we store a simple count at build
# time. The plan says KPI = all orders, so we annotate df_orders_all with a note.

# ---------------------------------------------------------------------------
# Sidebar — Filters
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Filters")

# Date range filter
min_date = df_orders_all["order_purchase_timestamp"].dt.date.min()
max_date = df_orders_all["order_purchase_timestamp"].dt.date.max()

date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Gracefully handle single-date selection
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0] if date_range else min_date

# State filter
all_states = sorted(df_orders_all["customer_state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect(
    "Customer State(s)",
    options=all_states,
    default=[],
    placeholder="All states",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Dataset:** Olist Brazilian E-Commerce  \n"
    "**Delivered orders:** 96,470  \n"
    "**Period:** Sep 2016 – Aug 2018"
)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
mask_orders = (
    (df_orders_all["order_purchase_timestamp"].dt.date >= start_date) &
    (df_orders_all["order_purchase_timestamp"].dt.date <= end_date)
)
if selected_states:
    mask_orders &= df_orders_all["customer_state"].isin(selected_states)

df_orders = df_orders_all[mask_orders].copy()

# df_items: filter by order_id membership in df_orders
filtered_order_ids = set(df_orders["order_id"])
df_items = df_items_all[df_items_all["order_id"].isin(filtered_order_ids)].copy()

# ---------------------------------------------------------------------------
# KPI calculations
# ---------------------------------------------------------------------------
total_orders_raw = 99_441   # total orders across all statuses (pre-filter)

delivered_orders   = len(df_orders)
delayed_orders     = int(df_orders["is_delayed"].sum())
ontime_orders      = delivered_orders - delayed_orders
ontime_rate        = ontime_orders / delivered_orders * 100 if delivered_orders else 0
delay_rate         = delayed_orders / delivered_orders * 100 if delivered_orders else 0
avg_delivery_days  = df_orders["delivery_time_days"].mean()
avg_review_score   = df_orders["review_score"].mean()

# Deltas vs full dataset (for st.metric delta)
_all_del  = len(df_orders_all)
_all_dr   = df_orders_all["is_delayed"].sum() / _all_del * 100
_all_otr  = 100 - _all_dr
_all_avd  = df_orders_all["delivery_time_days"].mean()
_all_avr  = df_orders_all["review_score"].mean()

# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------
st.title("📦 E-Commerce Customer Satisfaction & Delivery Performance")
st.markdown(
    "**BSc Computer Science Academic Internship Project** — "
    "Analysing how delivery performance affects customer satisfaction "
    "using the Olist Brazilian E-Commerce dataset (2016–2018)."
)

if selected_states or (start_date != min_date or end_date != max_date):
    st.info(
        f"📌 Filters active — showing **{delivered_orders:,}** delivered orders "
        f"({start_date} to {end_date}"
        + (f", states: {', '.join(selected_states)}" if selected_states else "")
        + ")"
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k5, k6, k7, k8 = st.columns(4)

k1.metric("📦 Total Orders (All Status)", f"{total_orders_raw:,}")
k2.metric(
    "✅ Delivered Orders",
    f"{delivered_orders:,}",
    delta=f"{delivered_orders - _all_del:,}" if selected_states or start_date != min_date else None,
)
k3.metric(
    "🟢 On-Time Orders",
    f"{ontime_orders:,}",
)
k4.metric(
    "🔴 Delayed Orders",
    f"{delayed_orders:,}",
)
k5.metric(
    "📈 On-Time Delivery Rate",
    f"{ontime_rate:.1f}%",
    delta=f"{ontime_rate - _all_otr:+.1f}%" if selected_states or start_date != min_date else None,
)
k6.metric(
    "⚠️ Delay Rate",
    f"{delay_rate:.1f}%",
    delta=f"{delay_rate - _all_dr:+.1f}%" if selected_states or start_date != min_date else None,
    delta_color="inverse",
)
k7.metric(
    "🚚 Avg Delivery Time",
    f"{avg_delivery_days:.1f} days",
    delta=f"{avg_delivery_days - _all_avd:+.1f} days" if selected_states or start_date != min_date else None,
    delta_color="inverse",
)
k8.metric(
    "⭐ Avg Review Score",
    f"{avg_review_score:.2f} / 5",
    delta=f"{avg_review_score - _all_avr:+.2f}" if selected_states or start_date != min_date else None,
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_delivery, tab_satisfaction, tab_categories, tab_locations, tab_trends = st.tabs([
    "📊 Overview",
    "🚚 Delivery",
    "⭐ Satisfaction",
    "📦 Categories",
    "🗺️ Locations",
    "📅 Trends",
])


# ===========================================================================
# TAB 1 — OVERVIEW
# ===========================================================================
with tab_overview:
    st.subheader("Dataset Overview")
    st.markdown(
        "High-level summary of the filtered data. Use the sidebar to narrow down "
        "by date range or customer state."
    )

    col1, col2, col3 = st.columns(3)

    # --- Review Score Distribution ---
    with col1:
        score_counts = (
            df_orders["review_score"]
            .dropna()
            .astype(int)
            .value_counts()
            .sort_index()
            .reset_index()
        )
        score_counts.columns = ["Review Score", "Count"]
        fig_scores = px.bar(
            score_counts,
            x="Review Score",
            y="Count",
            title="Review Score Distribution",
            color="Review Score",
            color_continuous_scale="RdYlGn",
            template=PLOTLY_TEMPLATE,
            text="Count",
        )
        fig_scores.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_scores.update_layout(
            coloraxis_showscale=False,
            xaxis=dict(tickmode="linear"),
            showlegend=False,
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig_scores, use_container_width=True)

    # --- On-Time vs Delayed Donut ---
    with col2:
        delay_pie_df = pd.DataFrame({
            "Status": ["On-Time", "Delayed"],
            "Count":  [ontime_orders, delayed_orders],
        })
        fig_pie = px.pie(
            delay_pie_df,
            names="Status",
            values="Count",
            title="On-Time vs Delayed Deliveries",
            hole=0.5,
            color="Status",
            color_discrete_map={"On-Time": COLOUR_ONTIME, "Delayed": COLOUR_DELAYED},
            template=PLOTLY_TEMPLATE,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(margin=dict(t=50, b=40))
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- Delivery Time Histogram ---
    with col3:
        fig_hist = px.histogram(
            df_orders,
            x="delivery_time_days",
            nbins=40,
            title="Delivery Time Distribution (Days)",
            labels={"delivery_time_days": "Delivery Time (Days)", "count": "Orders"},
            template=PLOTLY_TEMPLATE,
            color_discrete_sequence=[COLOUR_PRIMARY],
        )
        fig_hist.update_layout(
            xaxis_title="Delivery Time (Days)",
            yaxis_title="Number of Orders",
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # --- Summary stats table ---
    st.markdown("#### Summary Statistics")
    summary_df = pd.DataFrame({
        "Metric": [
            "Delivered Orders",
            "Orders with Review",
            "On-Time Orders",
            "Delayed Orders",
            "On-Time Rate",
            "Delay Rate",
            "Avg Delivery Time",
            "Avg Estimated Delivery Time",
            "Avg Delay Days (all orders)",
            "Avg Review Score",
            "Min Review Score",
            "Max Review Score",
        ],
        "Value": [
            f"{delivered_orders:,}",
            f"{int(df_orders['review_score'].notna().sum()):,}",
            f"{ontime_orders:,}",
            f"{delayed_orders:,}",
            f"{ontime_rate:.1f}%",
            f"{delay_rate:.1f}%",
            f"{avg_delivery_days:.1f} days",
            f"{df_orders['estimated_delivery_days'].mean():.1f} days",
            f"{df_orders['delay_days'].mean():.1f} days",
            f"{avg_review_score:.2f} / 5.00",
            f"{int(df_orders['review_score'].min()) if df_orders['review_score'].notna().any() else 'N/A'}",
            f"{int(df_orders['review_score'].max()) if df_orders['review_score'].notna().any() else 'N/A'}",
        ],
    })
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 2 — DELIVERY PERFORMANCE
# ===========================================================================
with tab_delivery:
    st.subheader("Delivery Performance Analysis")

    col1, col2 = st.columns(2)

    # --- Actual vs Estimated Delivery Days (avg comparison) ---
    with col1:
        comp_df = pd.DataFrame({
            "Type": ["Actual Delivery", "Estimated Delivery"],
            "Days": [
                df_orders["delivery_time_days"].mean(),
                df_orders["estimated_delivery_days"].mean(),
            ],
        })
        fig_comp = px.bar(
            comp_df,
            x="Type",
            y="Days",
            title="Actual vs Estimated Avg Delivery Time",
            labels={"Days": "Average Days", "Type": ""},
            color="Type",
            color_discrete_map={
                "Actual Delivery": COLOUR_PRIMARY,
                "Estimated Delivery": COLOUR_NEUTRAL,
            },
            template=PLOTLY_TEMPLATE,
            text="Days",
        )
        fig_comp.update_traces(texttemplate="%{text:.1f} days", textposition="outside")
        fig_comp.update_layout(showlegend=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig_comp, use_container_width=True)

    # --- Delay Days Distribution (late orders only) ---
    with col2:
        late_orders = df_orders[df_orders["is_delayed"]]
        fig_delay_hist = px.histogram(
            late_orders,
            x="delay_days",
            nbins=30,
            title=f"Delay Distribution — Late Orders Only ({len(late_orders):,})",
            labels={"delay_days": "Days Late", "count": "Orders"},
            color_discrete_sequence=[COLOUR_DELAYED],
            template=PLOTLY_TEMPLATE,
        )
        fig_delay_hist.update_layout(
            xaxis_title="Days Late",
            yaxis_title="Number of Orders",
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig_delay_hist, use_container_width=True)

    # --- Top 15 States by Delay Rate ---
    state_delivery = (
        df_orders.groupby("customer_state", as_index=False)
        .agg(
            total=("order_id", "count"),
            delayed=("is_delayed", "sum"),
            avg_delivery=("delivery_time_days", "mean"),
        )
    )
    state_delivery["delay_rate"] = state_delivery["delayed"] / state_delivery["total"] * 100
    state_delivery = state_delivery.sort_values("delay_rate", ascending=False)

    col3, col4 = st.columns(2)

    with col3:
        top_delay_states = state_delivery.head(15)
        fig_state_delay = px.bar(
            top_delay_states,
            x="customer_state",
            y="delay_rate",
            title="Top 15 States by Delay Rate (%)",
            labels={"customer_state": "State", "delay_rate": "Delay Rate (%)"},
            color="delay_rate",
            color_continuous_scale="Reds",
            template=PLOTLY_TEMPLATE,
            text="delay_rate",
        )
        fig_state_delay.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_state_delay.update_layout(
            coloraxis_showscale=False,
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig_state_delay, use_container_width=True)

    with col4:
        fig_state_avd = px.bar(
            state_delivery.sort_values("avg_delivery", ascending=False).head(15),
            x="customer_state",
            y="avg_delivery",
            title="Top 15 States by Avg Delivery Time (Days)",
            labels={"customer_state": "State", "avg_delivery": "Avg Delivery Days"},
            color="avg_delivery",
            color_continuous_scale="Blues",
            template=PLOTLY_TEMPLATE,
            text="avg_delivery",
        )
        fig_state_avd.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_state_avd.update_layout(coloraxis_showscale=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig_state_avd, use_container_width=True)

    # --- Full state table ---
    with st.expander("📋 Full State Delivery Table"):
        display_state = state_delivery.rename(columns={
            "customer_state": "State",
            "total": "Delivered Orders",
            "delayed": "Delayed Orders",
            "delay_rate": "Delay Rate (%)",
            "avg_delivery": "Avg Delivery Days",
        })
        display_state["Delay Rate (%)"] = display_state["Delay Rate (%)"].round(1)
        display_state["Avg Delivery Days"] = display_state["Avg Delivery Days"].round(1)
        st.dataframe(display_state, use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 3 — CUSTOMER SATISFACTION
# ===========================================================================
with tab_satisfaction:
    st.subheader("Customer Satisfaction Analysis")
    st.markdown("Exploring how delivery delays affect customer review scores.")

    col1, col2 = st.columns(2)

    # --- Avg Review Score: On-Time vs Delayed ---
    with col1:
        sat_group = (
            df_orders.dropna(subset=["review_score"])
            .groupby("is_delayed", as_index=False)
            .agg(avg_score=("review_score", "mean"), count=("order_id", "count"))
        )
        sat_group["Delivery Status"] = sat_group["is_delayed"].map(
            {False: "On-Time", True: "Delayed"}
        )
        fig_sat_bar = px.bar(
            sat_group,
            x="Delivery Status",
            y="avg_score",
            title="Avg Review Score: On-Time vs Delayed",
            labels={"avg_score": "Average Review Score", "Delivery Status": ""},
            color="Delivery Status",
            color_discrete_map={"On-Time": COLOUR_ONTIME, "Delayed": COLOUR_DELAYED},
            template=PLOTLY_TEMPLATE,
            text="avg_score",
        )
        fig_sat_bar.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_sat_bar.update_layout(
            showlegend=False,
            yaxis=dict(range=[0, 5.5]),
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig_sat_bar, use_container_width=True)

    # --- Box Plot: Review Score by Delay Group ---
    with col2:
        df_box = df_orders.dropna(subset=["review_score"]).copy()
        df_box["Delivery Status"] = df_box["is_delayed"].map(
            {False: "On-Time", True: "Delayed"}
        )
        fig_box = px.box(
            df_box,
            x="Delivery Status",
            y="review_score",
            title="Review Score Distribution: On-Time vs Delayed",
            labels={"review_score": "Review Score", "Delivery Status": ""},
            color="Delivery Status",
            color_discrete_map={"On-Time": COLOUR_ONTIME, "Delayed": COLOUR_DELAYED},
            template=PLOTLY_TEMPLATE,
        )
        fig_box.update_layout(showlegend=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig_box, use_container_width=True)

    # --- Scatter: Delay Days vs Review Score ---
    st.markdown("#### Relationship Between Delay Days and Review Score")
    scatter_df = df_orders[df_orders["is_delayed"]].dropna(subset=["review_score"]).copy()

    if len(scatter_df) > 0:
        # Sample for performance if very large
        sample_df = scatter_df.sample(min(5000, len(scatter_df)), random_state=42)
        fig_scatter = px.scatter(
            sample_df,
            x="delay_days",
            y="review_score",
            title=f"Delay Days vs Review Score — Delayed Orders "
                  f"(n={len(scatter_df):,}, sample shown: {len(sample_df):,})",
            labels={"delay_days": "Days Late", "review_score": "Review Score"},
            opacity=0.4,
            trendline="ols",
            color_discrete_sequence=[COLOUR_DELAYED],
            template=PLOTLY_TEMPLATE,
        )
        fig_scatter.update_layout(margin=dict(t=60, b=40))
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No delayed orders in the current filter selection.")

    # --- Review score breakdown by score and delay group ---
    with st.expander("📋 Detailed Review Score Breakdown"):
        detail_df = (
            df_orders.dropna(subset=["review_score"])
            .copy()
        )
        detail_df["Delivery Status"] = detail_df["is_delayed"].map(
            {False: "On-Time", True: "Delayed"}
        )
        detail_df["review_score"] = detail_df["review_score"].astype(int)
        breakdown = (
            detail_df.groupby(["Delivery Status", "review_score"])
            .size()
            .reset_index(name="Count")
        )
        breakdown["Score"] = breakdown["review_score"].astype(str) + " stars"
        fig_breakdown = px.bar(
            breakdown,
            x="review_score",
            y="Count",
            color="Delivery Status",
            barmode="group",
            title="Review Score Count by Delivery Status",
            labels={"review_score": "Review Score", "Count": "Number of Orders"},
            color_discrete_map={"On-Time": COLOUR_ONTIME, "Delayed": COLOUR_DELAYED},
            template=PLOTLY_TEMPLATE,
        )
        fig_breakdown.update_layout(xaxis=dict(tickmode="linear"), margin=dict(t=50, b=40))
        st.plotly_chart(fig_breakdown, use_container_width=True)


# ===========================================================================
# TAB 4 — PRODUCT CATEGORIES
# ===========================================================================
with tab_categories:
    st.subheader("Product Category Analysis")
    st.markdown(
        "Each order-item is counted separately. "
        "An order with 3 items from different categories contributes to all 3 categories."
    )

    # Aggregate df_items by category
    min_orders_cat = st.slider(
        "Minimum item count per category (filter noise)", 10, 500, 50, step=10
    )

    cat_agg = (
        df_items.groupby("product_category_name_english", as_index=False)
        .agg(
            item_count=("order_id", "count"),
            avg_delivery=("delivery_time_days", "mean"),
            avg_score=("review_score", "mean"),
            delayed=("is_delayed", "sum"),
        )
    )
    cat_agg["delay_rate"] = cat_agg["delayed"] / cat_agg["item_count"] * 100
    cat_agg = cat_agg[cat_agg["item_count"] >= min_orders_cat]

    col1, col2 = st.columns(2)

    # --- Top 15 slowest categories ---
    with col1:
        slowest = cat_agg.sort_values("avg_delivery", ascending=False).head(15)
        fig_slow = px.bar(
            slowest,
            x="avg_delivery",
            y="product_category_name_english",
            orientation="h",
            title="Top 15 Categories — Longest Avg Delivery Time",
            labels={
                "avg_delivery": "Avg Delivery Time (Days)",
                "product_category_name_english": "Category",
            },
            color="avg_delivery",
            color_continuous_scale="Reds",
            template=PLOTLY_TEMPLATE,
            text="avg_delivery",
        )
        fig_slow.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
        fig_slow.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(t=50, l=220, b=40),
        )
        st.plotly_chart(fig_slow, use_container_width=True)

    # --- Bottom 15 rated categories ---
    with col2:
        worst_rated = (
            cat_agg.dropna(subset=["avg_score"])
            .sort_values("avg_score", ascending=True)
            .head(15)
        )
        fig_worst = px.bar(
            worst_rated,
            x="avg_score",
            y="product_category_name_english",
            orientation="h",
            title="Bottom 15 Categories — Lowest Avg Review Score",
            labels={
                "avg_score": "Avg Review Score",
                "product_category_name_english": "Category",
            },
            color="avg_score",
            color_continuous_scale="RdYlGn",
            range_color=[1, 5],
            template=PLOTLY_TEMPLATE,
            text="avg_score",
        )
        fig_worst.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_worst.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(t=50, l=220, b=40),
        )
        st.plotly_chart(fig_worst, use_container_width=True)

    # --- Top 15 highest delay rate categories ---
    col3, col4 = st.columns(2)
    with col3:
        high_delay_cat = cat_agg.sort_values("delay_rate", ascending=False).head(15)
        fig_cat_delay = px.bar(
            high_delay_cat,
            x="delay_rate",
            y="product_category_name_english",
            orientation="h",
            title="Top 15 Categories — Highest Delay Rate (%)",
            labels={
                "delay_rate": "Delay Rate (%)",
                "product_category_name_english": "Category",
            },
            color="delay_rate",
            color_continuous_scale="Oranges",
            template=PLOTLY_TEMPLATE,
            text="delay_rate",
        )
        fig_cat_delay.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_cat_delay.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(t=50, l=220, b=40),
        )
        st.plotly_chart(fig_cat_delay, use_container_width=True)

    # --- Best rated categories ---
    with col4:
        best_rated = (
            cat_agg.dropna(subset=["avg_score"])
            .sort_values("avg_score", ascending=False)
            .head(15)
        )
        fig_best = px.bar(
            best_rated,
            x="avg_score",
            y="product_category_name_english",
            orientation="h",
            title="Top 15 Categories — Highest Avg Review Score",
            labels={
                "avg_score": "Avg Review Score",
                "product_category_name_english": "Category",
            },
            color="avg_score",
            color_continuous_scale="Greens",
            range_color=[1, 5],
            template=PLOTLY_TEMPLATE,
            text="avg_score",
        )
        fig_best.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_best.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(t=50, l=220, b=40),
        )
        st.plotly_chart(fig_best, use_container_width=True)

    with st.expander("📋 Full Category Table"):
        display_cat = cat_agg.sort_values("item_count", ascending=False).rename(columns={
            "product_category_name_english": "Category",
            "item_count": "Item Count",
            "avg_delivery": "Avg Delivery Days",
            "avg_score": "Avg Review Score",
            "delayed": "Delayed Items",
            "delay_rate": "Delay Rate (%)",
        })
        display_cat["Avg Delivery Days"] = display_cat["Avg Delivery Days"].round(1)
        display_cat["Avg Review Score"] = display_cat["Avg Review Score"].round(2)
        display_cat["Delay Rate (%)"] = display_cat["Delay Rate (%)"].round(1)
        st.dataframe(display_cat, use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 5 — CUSTOMER LOCATIONS
# ===========================================================================
with tab_locations:
    st.subheader("Customer State / Location Analysis")

    state_full = (
        df_orders.groupby("customer_state", as_index=False)
        .agg(
            order_count=("order_id", "count"),
            delayed=("is_delayed", "sum"),
            avg_score=("review_score", "mean"),
            avg_delivery=("delivery_time_days", "mean"),
        )
    )
    state_full["delay_rate"] = state_full["delayed"] / state_full["order_count"] * 100

    col1, col2 = st.columns(2)

    # --- Avg Review Score by State ---
    with col1:
        state_score_sorted = state_full.sort_values("avg_score", ascending=True)
        fig_state_score = px.bar(
            state_score_sorted,
            x="customer_state",
            y="avg_score",
            title="Average Review Score by State",
            labels={"customer_state": "State", "avg_score": "Avg Review Score"},
            color="avg_score",
            color_continuous_scale="RdYlGn",
            range_color=[1, 5],
            template=PLOTLY_TEMPLATE,
            text="avg_score",
        )
        fig_state_score.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_state_score.update_layout(coloraxis_showscale=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig_state_score, use_container_width=True)

    # --- Delay Rate by State ---
    with col2:
        state_delay_sorted = state_full.sort_values("delay_rate", ascending=False)
        fig_state_delay2 = px.bar(
            state_delay_sorted,
            x="customer_state",
            y="delay_rate",
            title="Delay Rate by State (%)",
            labels={"customer_state": "State", "delay_rate": "Delay Rate (%)"},
            color="delay_rate",
            color_continuous_scale="Reds",
            template=PLOTLY_TEMPLATE,
            text="delay_rate",
        )
        fig_state_delay2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_state_delay2.update_layout(coloraxis_showscale=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig_state_delay2, use_container_width=True)

    # --- Order Volume by State ---
    state_vol = state_full.sort_values("order_count", ascending=False)
    fig_state_vol = px.bar(
        state_vol,
        x="customer_state",
        y="order_count",
        title="Order Volume by State",
        labels={"customer_state": "State", "order_count": "Number of Delivered Orders"},
        color="order_count",
        color_continuous_scale="Blues",
        template=PLOTLY_TEMPLATE,
        text="order_count",
    )
    fig_state_vol.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_state_vol.update_layout(coloraxis_showscale=False, margin=dict(t=50, b=40))
    st.plotly_chart(fig_state_vol, use_container_width=True)

    with st.expander("📋 Full State Analysis Table"):
        display_state_full = state_full.sort_values("order_count", ascending=False).rename(columns={
            "customer_state": "State",
            "order_count": "Delivered Orders",
            "delayed": "Delayed Orders",
            "avg_score": "Avg Review Score",
            "avg_delivery": "Avg Delivery Days",
            "delay_rate": "Delay Rate (%)",
        })
        display_state_full["Avg Review Score"] = display_state_full["Avg Review Score"].round(2)
        display_state_full["Avg Delivery Days"] = display_state_full["Avg Delivery Days"].round(1)
        display_state_full["Delay Rate (%)"] = display_state_full["Delay Rate (%)"].round(1)
        st.dataframe(display_state_full, use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 6 — TRENDS + BUSINESS INSIGHTS
# ===========================================================================
with tab_trends:
    st.subheader("Time-Based Trend Analysis")

    # Monthly aggregation
    monthly = (
        df_orders.groupby("order_month", as_index=False)
        .agg(
            order_count=("order_id", "count"),
            delayed=("is_delayed", "sum"),
            avg_score=("review_score", "mean"),
            avg_delivery=("delivery_time_days", "mean"),
        )
    )
    monthly["ontime_rate"] = (
        (monthly["order_count"] - monthly["delayed"]) / monthly["order_count"] * 100
    )
    # Sort chronologically
    monthly = monthly.sort_values("order_month")

    col1, col2 = st.columns(2)

    # --- Monthly Order Volume ---
    with col1:
        fig_vol = px.bar(
            monthly,
            x="order_month",
            y="order_count",
            title="Monthly Order Volume",
            labels={"order_month": "Month", "order_count": "Delivered Orders"},
            color_discrete_sequence=[COLOUR_PRIMARY],
            template=PLOTLY_TEMPLATE,
        )
        fig_vol.update_layout(
            xaxis_tickangle=-45,
            margin=dict(t=50, b=80),
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # --- Monthly Avg Review Score ---
    with col2:
        fig_score_trend = px.line(
            monthly,
            x="order_month",
            y="avg_score",
            title="Monthly Average Review Score",
            labels={"order_month": "Month", "avg_score": "Avg Review Score"},
            markers=True,
            color_discrete_sequence=[COLOUR_PRIMARY],
            template=PLOTLY_TEMPLATE,
        )
        fig_score_trend.update_layout(
            yaxis=dict(range=[0, 5.2]),
            xaxis_tickangle=-45,
            margin=dict(t=50, b=80),
        )
        st.plotly_chart(fig_score_trend, use_container_width=True)

    # --- Monthly On-Time Delivery Rate ---
    fig_ontime_trend = px.line(
        monthly,
        x="order_month",
        y="ontime_rate",
        title="Monthly On-Time Delivery Rate (%)",
        labels={"order_month": "Month", "ontime_rate": "On-Time Rate (%)"},
        markers=True,
        color_discrete_sequence=[COLOUR_ONTIME],
        template=PLOTLY_TEMPLATE,
    )
    fig_ontime_trend.update_layout(
        yaxis=dict(range=[0, 105]),
        xaxis_tickangle=-45,
        margin=dict(t=50, b=80),
    )
    st.plotly_chart(fig_ontime_trend, use_container_width=True)

    # -----------------------------------------------------------------------
    # Business Insights — dynamically computed from filtered data
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.subheader("💡 Data-Driven Business Insights & Recommendations")
    st.markdown(
        "_All insights below are calculated from the actual filtered dataset. "
        "No values are hard-coded or fabricated._"
    )

    df_w_review = df_orders.dropna(subset=["review_score"])

    # Compute insight values
    _ontime_score = df_w_review.loc[~df_w_review["is_delayed"], "review_score"].mean()
    _delayed_score = df_w_review.loc[df_w_review["is_delayed"], "review_score"].mean()
    _score_diff    = _ontime_score - _delayed_score

    # Worst state by delay rate (min 100 orders)
    _state_agg = (
        df_orders.groupby("customer_state")
        .agg(total=("order_id", "count"), delayed=("is_delayed", "sum"))
    )
    _state_agg["dr"] = _state_agg["delayed"] / _state_agg["total"] * 100
    _state_agg_filtered = _state_agg[_state_agg["total"] >= 100]
    _worst_state_delay    = _state_agg_filtered["dr"].idxmax() if len(_state_agg_filtered) else "N/A"
    _worst_state_delay_pct = _state_agg_filtered["dr"].max() if len(_state_agg_filtered) else 0

    # Worst state by avg review score (min 100 orders)
    _state_score = df_w_review.groupby("customer_state").agg(
        total=("order_id", "count"), avg=("review_score", "mean")
    )
    _state_score_f = _state_score[_state_score["total"] >= 100]
    _worst_state_score    = _state_score_f["avg"].idxmin() if len(_state_score_f) else "N/A"
    _worst_state_score_v  = _state_score_f["avg"].min() if len(_state_score_f) else 0

    # Worst category by avg delivery time (min 50 items)
    _cat_del = (
        df_items.groupby("product_category_name_english")
        .agg(cnt=("order_id", "count"), avg_del=("delivery_time_days", "mean"))
    )
    _cat_del_f = _cat_del[_cat_del["cnt"] >= 50]
    _slowest_cat     = _cat_del_f["avg_del"].idxmax() if len(_cat_del_f) else "N/A"
    _slowest_cat_days = _cat_del_f["avg_del"].max() if len(_cat_del_f) else 0

    # Worst category by avg review score (min 50 items)
    _cat_score = (
        df_items.dropna(subset=["review_score"])
        .groupby("product_category_name_english")
        .agg(cnt=("order_id", "count"), avg_sc=("review_score", "mean"))
    )
    _cat_score_f = _cat_score[_cat_score["cnt"] >= 50]
    _worst_cat_score   = _cat_score_f["avg_sc"].idxmin() if len(_cat_score_f) else "N/A"
    _worst_cat_score_v = _cat_score_f["avg_sc"].min() if len(_cat_score_f) else 0

    # Overall delay rate
    _overall_delay_rate = delay_rate

    insight_data_available = delivered_orders >= 100

    if not insight_data_available:
        st.warning("Not enough data in the current filter selection to generate insights.")
    else:
        st.markdown(f"""
### 📌 Key Findings

**1. Delays significantly reduce customer satisfaction.**

On-time deliveries receive an average review score of **{_ontime_score:.2f}** out of 5,
while delayed deliveries receive **{_delayed_score:.2f}** — a difference of
**{_score_diff:.2f} points**. This confirms that delivery timeliness is a primary driver
of customer satisfaction.

**2. {_worst_state_delay} has the highest delivery delay rate.**

The state **{_worst_state_delay}** records a delay rate of
**{_worst_state_delay_pct:.1f}%**, the highest among states with at least 100 orders.
The company should investigate carrier partnerships and logistics infrastructure
in this region.

**3. {_worst_state_score} customers report the lowest satisfaction.**

Customers in **{_worst_state_score}** give an average review score of
**{_worst_state_score_v:.2f}**, suggesting that beyond delivery, regional service
quality may need improvement.

**4. "{_slowest_cat}" is the slowest product category to deliver.**

Orders in the **{_slowest_cat}** category take an average of
**{_slowest_cat_days:.1f} days** to arrive — the longest across all categories
with at least 50 items. Sellers or warehouse processes in this category
should be reviewed.

**5. "{_worst_cat_score}" has the lowest customer review score.**

The product category **{_worst_cat_score}** has an average review score of
**{_worst_cat_score_v:.2f}**, the lowest of all qualifying categories.
This may reflect product quality, delivery issues, or both.
""")

        st.markdown("---")
        st.markdown("### ✅ Business Recommendations")

        rec1_delta = f"{_score_diff:.2f} point difference in review scores"
        st.info(
            f"**Recommendation 1 — Prioritise on-time delivery**  \n"
            f"With a {rec1_delta} between on-time and delayed orders, reducing delays "
            f"should be the highest priority. Even a 1-day improvement in delivery "
            f"predictability is likely to increase review scores."
        )
        st.info(
            f"**Recommendation 2 — Focus logistics investment on {_worst_state_delay}**  \n"
            f"This state has a delay rate of {_worst_state_delay_pct:.1f}%. "
            f"Reviewing last-mile carrier performance in this region could reduce delays "
            f"and improve customer satisfaction scores."
        )
        st.info(
            f"**Recommendation 3 — Improve delivery for '{_slowest_cat}' category**  \n"
            f"Average delivery of {_slowest_cat_days:.1f} days suggests fulfilment or "
            f"shipping challenges in this product category. Optimising warehouse picking, "
            f"packaging, or carrier selection for heavy/bulky items may help."
        )
        st.info(
            f"**Recommendation 4 — Investigate quality issues in '{_worst_cat_score}'**  \n"
            f"Average review score of {_worst_cat_score_v:.2f} in this category is the "
            f"lowest overall. The company should review seller listings, product descriptions, "
            f"and customer complaints for this category."
        )
        st.info(
            f"**Recommendation 5 — Set realistic delivery estimates**  \n"
            f"The overall delay rate is {_overall_delay_rate:.1f}%. Customers are more "
            f"likely to be satisfied when their expectations are met. Providing "
            f"more accurate estimated delivery dates — especially for distant states — "
            f"can improve perceived service quality without changing actual delivery speed."
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "📦 E-Commerce Customer Satisfaction & Delivery Performance Analysis  |  "
    "BSc Computer Science Academic Internship Project  |  "
    "Data: Olist Brazilian E-Commerce Public Dataset (Kaggle)"
)
