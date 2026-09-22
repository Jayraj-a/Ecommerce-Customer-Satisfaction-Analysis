# E-Commerce Customer Satisfaction & Delivery Performance Analysis

A BSc Computer Science academic internship project analysing how delivery
performance affects customer satisfaction using the
[Olist Brazilian E-Commerce public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

---

## Project Structure

```
Ecommerce_Customer_Satisfaction_Project/
├── data/                         # Raw CSV datasets (not committed — add manually)
│   ├── olist_orders_dataset.csv
│   ├── olist_customers_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_products_dataset.csv
│   └── product_category_name_translation.csv
├── app.py                        # Streamlit dashboard (main entry point)
├── data_processing.py            # Data loading, cleaning, and merging logic
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## Dataset

Six CSV files from the Olist Brazilian E-Commerce public dataset (Kaggle):

| File | Rows | Description |
|---|---|---|
| `olist_orders_dataset.csv` | 99,441 | Order lifecycle — status, timestamps, delivery dates |
| `olist_customers_dataset.csv` | 99,441 | Customer identity and geographic state |
| `olist_order_items_dataset.csv` | 112,650 | Line items per order — product, price, freight |
| `olist_order_reviews_dataset.csv` | 99,224 | Customer review scores (1–5) per order |
| `olist_products_dataset.csv` | 32,951 | Product catalogue with category and dimensions |
| `product_category_name_translation.csv` | 71 | Portuguese → English category name mapping |

**Coverage:** Sep 2016 – Aug 2018 · **Delivered orders analysed:** 96,470

---

## Setup

### 1. Clone / extract the project

```bash
git clone <repo-url>
cd Ecommerce_Customer_Satisfaction_Project
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies: `pandas>=2.0`, `plotly>=5.0`, `streamlit>=1.35`, `statsmodels>=0.14`

### 4. Add the data files

Place all six CSV files inside the `data/` directory (create it if absent):

```
data/
├── olist_orders_dataset.csv
├── olist_customers_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_products_dataset.csv
└── product_category_name_translation.csv
```

---

## Running the Dashboard

```bash
streamlit run app.py
```

Opens at **http://localhost:8501** in your browser.

---

## Dashboard Features

### Sidebar Filters
- **Order Date Range** — narrow analysis to any date window within Sep 2016 – Aug 2018
- **Customer State(s)** — filter to one or more Brazilian states; all states shown by default

All 8 KPI cards and every chart update instantly when filters change.

### KPI Cards (two rows of four)
| KPI | Description |
|---|---|
| Total Orders (All Statuses) | 99,441 orders across all order statuses |
| Delivered Orders | Orders with `order_status = 'delivered'` and a recorded delivery date |
| On-Time Orders | Delivered orders where actual ≤ estimated delivery date |
| Delayed Orders | Delivered orders where actual > estimated delivery date |
| On-Time Delivery Rate | On-time orders ÷ delivered orders |
| Delay Rate | Delayed orders ÷ delivered orders |
| Avg Delivery Time | Mean calendar days from purchase to delivery |
| Avg Review Score | Mean customer review score (1–5) |

### Tabs

| Tab | Content |
|---|---|
| 📊 **Overview** | Review score distribution · On-time vs delayed donut · Delivery time histogram · Summary statistics table |
| 🚚 **Delivery** | Actual vs estimated delivery bar · Delay distribution histogram · Top 15 states by delay rate · Top 15 states by avg delivery time · Full state delivery table |
| ⭐ **Satisfaction** | Avg score by delay group · Box plot by delay group · Delay days vs review score scatter (with OLS trendline) · Score breakdown by delivery status |
| 📦 **Categories** | Slowest 15 categories · Lowest-rated 15 categories · Highest delay rate 15 categories · Best-rated 15 categories · Full category table |
| 🗺️ **Locations** | Avg review score by state · Delay rate by state · Order volume by state · Full state analysis table |
| 📅 **Trends** | Monthly order volume · Monthly avg review score · Monthly on-time delivery rate · Data-driven business insights & recommendations |

---

## Data Pipeline

Two analytical DataFrames are built in `data_processing.py`:

- **`df_orders`** — one row per delivered order (96,470 rows). Used for delivery KPIs, satisfaction analysis, state analysis, and time trends.
- **`df_items`** — one row per delivered order-item (110,189 rows). Used exclusively for product category analysis to avoid double-counting orders.

Key computed columns: `delivery_time_days`, `estimated_delivery_days`, `delay_days`, `is_delayed`, `order_month`.

Duplicate reviews: where an order has multiple reviews, the **latest** (`review_creation_date` descending) is kept.

---

## Key Business Questions Addressed

1. Are delayed deliveries associated with lower customer review scores?
2. Which Brazilian states experience the highest delivery delay rates?
3. Which product categories have the longest average delivery times?
4. Which product categories receive the lowest average review scores?
5. How does actual delivery time compare with estimated delivery dates?
6. How do delivery performance and customer satisfaction evolve over time?

---

## Notes

- All KPI values, charts, insights, and recommendations are calculated at runtime from the actual filtered dataset. No values are fabricated or hard-coded.
- The OLS trendline in the scatter chart requires `statsmodels` (included in `requirements.txt`).
- The `data/` directory is not committed to version control. Ensure the six CSV files are present locally before running the app.
