import os

import pandas as pd
import psycopg
import streamlit as st

st.set_page_config(page_title="ShopPulse", page_icon="🛒", layout="wide")
st.title("ShopPulse")
st.caption("E-commerce CSV analytics · PostgreSQL · completed orders · USD")
st.button("Refresh data")

try:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        # All charts and metrics come from the same published snapshot.
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")

        def query(view):
            cur = conn.execute(f"SELECT * FROM marts.{view}")
            return pd.DataFrame(cur.fetchall(), columns=[col.name for col in cur.description])

        kpis = query("kpis").iloc[0]
        daily = query("daily_revenue").sort_values("day")
        products = query("top_products").sort_values("revenue", ascending=False)
        retention = query("cohort_retention").sort_values(["cohort_month", "month_number"])
except (psycopg.Error, KeyError) as exc:
    st.warning("Analytics unavailable. Run `make pipeline`, then refresh this page.")
    st.stop()

labels = [("Revenue", f"${kpis.revenue:,.2f}"),
          ("Completed orders", int(kpis.completed_orders)),
          ("Purchasing customers", int(kpis.purchasing_customers)),
          ("Average order value", f"${kpis.average_order_value:,.2f}"),
          ("Repeat customers", int(kpis.repeat_customers)),
          ("Units sold", int(kpis.units_sold))]
for col, (label, value) in zip(st.columns(6), labels):
    col.metric(label, value)

left, right = st.columns(2)
with left:
    st.subheader("Daily revenue")
    if not daily.empty:
        daily["revenue"] = daily["revenue"].astype(float)
        daily["day"] = pd.to_datetime(daily["day"])
        daily = daily.set_index("day").asfreq("D", fill_value=0)
        st.line_chart(daily[["revenue"]], color="#16a085")
with right:
    st.subheader("Top products by revenue")
    products["revenue"] = products["revenue"].astype(float)
    products["product"] = products["product_name"] + " (#" + products["product_id"].astype(str) + ")"
    st.bar_chart(products.set_index("product")[["revenue"]], color="#2980b9")

st.subheader("Monthly purchase retention")
st.caption("Cohort = first completed purchase month. Only months with purchases are shown; absent months may mean zero activity or no observation yet.")
st.dataframe(retention, hide_index=True, use_container_width=True)
st.caption("Revenue excludes pending/cancelled orders. No tax, shipping, refunds or currency conversion in this MVP.")
