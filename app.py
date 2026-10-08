"""Streamlit PQR (Product Quality Report) prototype dashboard.

PQR rate = complaints per 10,000 gallons of paint.
Each batch is 10,000 gallons, so rate = complaints / batches produced.
"""

from __future__ import annotations

import html
import os
import textwrap

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synthetic_data")
GALLONS_PER_BATCH = 10_000
MAX_HOVER_COMMENTS = 6
CATEGORY_BY_REASON = {
    "Color - Fade": "Quality Notification",
    "Alkalinity": "Quality Notification",
    "Chalking": "Quality Notification",
    "Foam": "Quality Notification",
    "Gassing": "Quality Notification",
    "Gelled": "Quality Notification",
    "Gloss and Sheen": "Quality Notification",
    "Gloss Fade": "Quality Notification",
    "Hide": "Quality Notification",
    "Mildew": "Quality Notification",
    "Odor": "Quality Notification",
    "Settling": "Quality Notification",
    "Skinning": "Quality Notification",
    "Adhesion": "Help Needed",
    "Application": "Help Needed",
    "Blocking": "Help Needed",
    "Burnishing": "Help Needed",
    "Flashing": "Help Needed",
    "Scrubbability": "Help Needed",
    "Package": "In-Store Resolution",
    "Product Satisfaction Guarantee": "In-Store Resolution",
    "Service Satisfaction Guarantee": "In-Store Resolution",
}

st.set_page_config(page_title="PQR Dashboard", page_icon="▦", layout="wide")

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#1f4e79", "#4f81a1", "#7f9db9", "#b7c9d6", "#d28b5d"]

st.markdown(
    """
    <style>
    :root {
        --navy: #17324d;
        --blue: #1f4e79;
        --muted: #687887;
        --line: #d8e0e6;
        --surface: #ffffff;
        --workspace: #f3f6f8;
    }
    .stAppViewContainer { background: var(--workspace); }
    .main .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background: var(--navy); }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown { color: #ffffff; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #ffffff;
        border-color: #9fb2c2;
    }
    h1, h2, h3, h4 { color: var(--navy); letter-spacing: 0; }
    h1 { font-size: 2rem; font-weight: 700; }
    h2, h3 { font-weight: 650; }
    [data-testid="stMetricValue"] { color: var(--navy); }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricDelta"] { font-size: 0.8rem; }
    [data-baseweb="tab-list"] { gap: 0.25rem; border-bottom: 1px solid var(--line); }
    [data-baseweb="tab"] { color: var(--muted); font-weight: 600; padding: 0.7rem 1rem; }
    [aria-selected="true"][data-baseweb="tab"] { color: var(--blue); }
    [data-baseweb="tab-highlight"] { background: var(--blue); }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 4px;
        box-shadow: 0 1px 2px rgba(23, 50, 77, 0.04);
    }
    .st-key-rex-year-panel, .st-key-rex-increase-panel,
    .st-key-rex-compare-panel, .st-key-rex-stats-panel,
    .st-key-rex-comments-panel, .st-key-product-year-panel,
    .st-key-product-increase-panel, .st-key-product-compare-panel,
    .st-key-product-stats-panel, .st-key-product-comments-panel {
        background: var(--surface);
        border-color: var(--line);
    }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(complaints_mtime: float = 0):
    complaints = pd.read_csv(os.path.join(DATA_DIR, "complaints.csv"), parse_dates=["Date"])
    if "Settlement_Total" not in complaints:
        ticket_numbers = complaints["Ticket_ID"].str.rsplit("-", n=1).str[-1].astype(int)
        complaints["Settlement_Total"] = (25 + (ticket_numbers * 7919 % 497500) / 100).round(2)
    batches = pd.read_csv(os.path.join(DATA_DIR, "batches.csv"), parse_dates=["Production_Date"])
    formulas = pd.read_csv(os.path.join(DATA_DIR, "formulas.csv"))
    complaints = complaints.merge(formulas, on="REX_Number", how="left")
    batches = batches.merge(formulas, on="REX_Number", how="left")
    return complaints, batches, formulas


def rex_summary(complaints: pd.DataFrame, batches: pd.DataFrame) -> pd.DataFrame:
    c = complaints.groupby("REX_Number").size().rename("Complaints")
    b = batches.groupby("REX_Number").size().rename("Batches")
    out = pd.concat([b, c], axis=1).fillna(0)
    out["Complaints"] = out["Complaints"].astype(int)
    out["Batches"] = out["Batches"].astype(int)
    out["Gallons"] = out["Batches"] * GALLONS_PER_BATCH
    out["PQR_Rate"] = (out["Complaints"] / out["Batches"]).round(3)
    return out.reset_index()


def hover_comments(group: pd.DataFrame) -> str:
    """Bullet list of actual complaint text for the plotly hover box."""
    rows = group.sort_values("Date", ascending=False).head(MAX_HOVER_COMMENTS)
    lines = []
    for r in rows.itertuples():
        wrapped = "<br>   ".join(textwrap.wrap(html.escape(r.Comments), 70))
        lines.append(f"• <i>{r.Ticket_ID} ({r.Date:%Y-%m-%d})</i><br>   {wrapped}")
    extra = len(group) - len(rows)
    if extra > 0:
        lines.append(f"<i>…and {extra:,} more</i>")
    return "<br>".join(lines)


try:
    complaints, batches, formulas = load_data(
        os.path.getmtime(os.path.join(DATA_DIR, "complaints.csv"))
    )
except FileNotFoundError:
    st.error("No data found. Run `python generate_data.py` first to create synthetic_data/.")
    st.stop()

if "Settlement_Total" not in complaints:
    ticket_numbers = complaints["Ticket_ID"].str.rsplit("-", n=1).str[-1].astype(int)
    complaints["Settlement_Total"] = (25 + (ticket_numbers * 7919 % 497500) / 100).round(2)

channel_to_market = {
    "Direct/Commercial": "PSG",
    "Big Box": "Retail",
    "Company Store": "Retail",
    "Dealer": "Retail",
}
region_to_division = {
    "West": "CAN",
    "Northeast": "EAD",
    "Midwest": "MWD",
    "Southeast": "SED",
    "Southwest": "SWD",
}
complaints["Market"] = complaints["Channel"].map(channel_to_market)
complaints["Division"] = complaints["Region"].map(region_to_division)
batch_dimensions = (complaints.groupby("Batch_Number")
                .agg(Market=("Market", lambda values: values.mode().iat[0]),
                    Division=("Division", lambda values: values.mode().iat[0]))
                .reset_index())
batches = batches.drop(columns=["Market", "Division"], errors="ignore").merge(
    batch_dimensions, on="Batch_Number", how="left"
)

market_options = ["All", "PSG", "Retail"]
division_options = ["All", "CAN", "EAD", "MWD", "SED", "SWD"]
st.session_state.setdefault("selected_market", "All")
st.session_state.setdefault("selected_division", "All")


def sync_page_filters(page_key: str) -> None:
    st.session_state["selected_market"] = st.session_state[f"{page_key}_market"]
    st.session_state["selected_division"] = st.session_state[f"{page_key}_division"]
    st.rerun()


def render_page_filters(page_key: str) -> None:
    filter_columns = st.columns(2)
    filter_columns[0].selectbox(
        "Market",
        market_options,
        index=market_options.index(st.session_state["selected_market"]),
        key=f"{page_key}_market",
        on_change=sync_page_filters,
        args=(page_key,),
    )
    filter_columns[1].selectbox(
        "Division",
        division_options,
        index=division_options.index(st.session_state["selected_division"]),
        key=f"{page_key}_division",
        on_change=sync_page_filters,
        args=(page_key,),
    )


selected_market = st.session_state["selected_market"]
selected_division = st.session_state["selected_division"]

with st.sidebar:
    st.header("Filters")
    render_page_filters("main")

if selected_market != "All":
    complaints = complaints[complaints["Market"] == selected_market]
    batches = batches[batches["Market"] == selected_market]
if selected_division != "All":
    complaints = complaints[complaints["Division"] == selected_division]
    batches = batches[batches["Division"] == selected_division]
if complaints.empty or batches.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

dashboard_tab, rex_tab, product_tab, batch_date_tab, all_trends_tab = st.tabs([
    "Overview", "REX view", "Product view", "Batch date view", "All trends explorer"
])

with rex_tab:
    st.subheader("REX view")

with product_tab:
    st.subheader("Product view")

with batch_date_tab:
    st.subheader("Batch date view")

dashboard_tab.__enter__()
st.title("PQR Overview")
metric = st.selectbox(
    "Metric",
    ["PQR count", "PQR rate", "Settlement total"],
    key="overview_metric",
)

complaints["Year"] = complaints["Date"].dt.year
batches["Year"] = batches["Production_Date"].dt.year
years = sorted(set(complaints["Year"]).union(batches["Year"]))

metric_formats = {
    "PQR count": lambda value: f"{value:,.0f}",
    "PQR rate": lambda value: f"{value:,.3f}",
    "Settlement total": lambda value: f"${value:,.2f}",
}
format_value = metric_formats[metric]


def measure(complaint_rows: pd.DataFrame, batch_rows: pd.DataFrame) -> float:
    if metric == "PQR count":
        return float(len(complaint_rows))
    if metric == "Settlement total":
        return float(complaint_rows["Settlement_Total"].sum())
    return float(len(complaint_rows) / len(batch_rows)) if len(batch_rows) else 0.0


def in_year(frame: pd.DataFrame, date_column: str, year: int) -> pd.DataFrame:
    return frame[frame[date_column].dt.year == year]


def in_month(frame: pd.DataFrame, date_column: str, period) -> pd.DataFrame:
    return frame[frame[date_column].dt.to_period("M") == period]


def delta_text(current: float, previous: float, label: str) -> str | None:
    if previous == 0:
        return None
    change = (current - previous) / previous * 100
    return f"{change:+.1f}% vs {label}"


current_year = int(max(years))
previous_year = current_year - 1
current_period = complaints.loc[complaints["Year"] == current_year, "Date"].dt.to_period("M").max()
previous_period = current_period - 1
current_period_label = current_period.strftime("%b %Y")
previous_period_label = previous_period.strftime("%b %Y")

year_value = measure(in_year(complaints, "Date", current_year),
                     in_year(batches, "Production_Date", current_year))
prior_year_value = measure(in_year(complaints, "Date", previous_year),
                           in_year(batches, "Production_Date", previous_year))

month_complaints = in_month(complaints, "Date", current_period)
month_batches = in_month(batches, "Production_Date", current_period)
month_value = measure(month_complaints, month_batches)
prior_month_value = measure(in_month(complaints, "Date", previous_period),
                            in_month(batches, "Production_Date", previous_period))

if month_complaints.empty:
    top_reason = None
    top_reason_value = 0.0
    prior_top_reason_value = 0.0
else:
    if metric == "Settlement total":
        reason_totals = month_complaints.groupby("Reason")["Settlement_Total"].sum()
    else:
        reason_totals = month_complaints.groupby("Reason").size()
    top_reason = reason_totals.idxmax()
    top_reason_value = measure(month_complaints[month_complaints["Reason"] == top_reason],
                               month_batches)
    prior_month_complaints = in_month(complaints, "Date", previous_period)
    prior_top_reason_value = measure(
        prior_month_complaints[prior_month_complaints["Reason"] == top_reason],
        in_month(batches, "Production_Date", previous_period),
    )

month_names = pd.DataFrame({
    "Month": range(1, 13),
    "Month name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
})
month_order = month_names["Month name"].tolist()

card_columns = st.columns(3)


def render_card(column, caption: str, label: str, value: str, delta: str | None) -> None:
    with column:
        box = st.container(border=True)
        box.markdown(f"#### {caption}")
        box.metric(label, value, delta=delta, delta_color="inverse")

render_card(
    card_columns[0],
    f"Year to date · {current_year}", metric, format_value(year_value),
    delta_text(year_value, prior_year_value, str(previous_year)),
)
render_card(
    card_columns[1],
    f"Current month · {current_period_label}", metric, format_value(month_value),
    delta_text(month_value, prior_month_value, previous_period_label),
)
render_card(
    card_columns[2],
    f"Top complaint this month · {current_period_label}",
    top_reason or "No complaints",
    format_value(top_reason_value) if top_reason else "—",
    delta_text(top_reason_value, prior_top_reason_value, previous_period_label)
    if top_reason else None,
)


def render_overview_trends() -> None:
    st.subheader("Yearly trend")
    if metric == "PQR count":
        year_metric = complaints.groupby("Year").size().rename("Value").reset_index()
        value_label = "PQR count"
        text_format = "%{text:,}"
    elif metric == "PQR rate":
        year_metric = (complaints.groupby("Year").size().rename("PQR count")
                       .to_frame().join(batches.groupby("Year").size().rename("Batches"))
                       .fillna(0).reset_index())
        year_metric["Value"] = year_metric["PQR count"].div(
            year_metric["Batches"].replace(0, pd.NA)
        ).fillna(0)
        value_label = "PQR rate"
        text_format = "%{text:.3f}"
    else:
        year_metric = (complaints.groupby("Year")["Settlement_Total"]
                       .sum().rename("Value").reset_index())
        value_label = "Settlement total"
        text_format = "$%{text:,.2f}"

    if metric == "PQR rate":
        year_fig = px.line(year_metric, x="Year", y="Value", text="Value", markers=True,
                           title=f"{metric} by year", labels={"Value": value_label})
        year_fig.update_traces(texttemplate=text_format, textposition="top center")
    else:
        year_fig = px.bar(year_metric, x="Year", y="Value", text="Value",
                          title=f"{metric} by year", labels={"Value": value_label})
        year_fig.update_traces(texttemplate=text_format, textposition="outside")
    year_fig.update_layout(height=380, xaxis=dict(type="category"))
    st.plotly_chart(year_fig, use_container_width=True)

    st.subheader("Monthly trend")
    scoped_complaints = complaints.copy()
    scoped_batches = batches.copy()
    scoped_complaints["Month"] = scoped_complaints["Date"].dt.month
    scoped_batches["Month"] = scoped_batches["Production_Date"].dt.month
    monthly_grid = pd.MultiIndex.from_product(
        [years, range(1, 13)], names=["Year", "Month"]
    ).to_frame(index=False)
    if metric == "PQR count":
        monthly_count = (scoped_complaints.groupby(["Year", "Month"]).size()
                         .rename("Value").reset_index())
        value_label = "PQR count"
        text_format = "%{text:,}"
    elif metric == "PQR rate":
        monthly_count = (scoped_complaints.groupby(["Year", "Month"]).size()
                         .rename("PQR count").to_frame()
                         .join(scoped_batches.groupby(["Year", "Month"]).size().rename("Batches"))
                         .fillna(0).reset_index())
        monthly_count["Value"] = monthly_count["PQR count"].div(
            monthly_count["Batches"].replace(0, pd.NA)
        ).fillna(0)
        value_label = "PQR rate"
        text_format = "%{text:.3f}"
    else:
        monthly_count = (scoped_complaints.groupby(["Year", "Month"])["Settlement_Total"]
                         .sum().rename("Value").reset_index())
        value_label = "Settlement total"
        text_format = "$%{text:,.2f}"
    monthly_count = (monthly_count.merge(monthly_grid, on=["Year", "Month"], how="right")
                     .merge(month_names, on="Month", how="left"))
    monthly_count["Value"] = monthly_count["Value"].fillna(0)
    monthly_count["Year"] = monthly_count["Year"].astype(str)
    monthly_fig = px.line(
        monthly_count, x="Month name", y="Value", color="Year", text="Value",
        markers=True, category_orders={"Month name": month_order},
        title=f"{metric} by month", labels={"Value": value_label},
    )
    monthly_fig.update_traces(texttemplate=text_format, textposition="top center")
    monthly_fig.update_layout(height=400, xaxis_title="Month", yaxis_title=value_label)
    st.plotly_chart(monthly_fig, use_container_width=True)
    monthly_table = (monthly_count.pivot(index="Year", columns="Month name", values="Value")
                     .reindex(columns=month_order, fill_value=0).fillna(0))
    monthly_table["Total"] = monthly_table.sum(axis=1)
    monthly_table = monthly_table.reset_index()
    numeric_columns = monthly_table.columns[1:]
    monthly_table[numeric_columns] = monthly_table[numeric_columns].map(
        lambda value: f"${value:,.2f}" if metric == "Settlement total"
        else f"{value:,.3f}" if metric == "PQR rate"
        else f"{value:,.0f}"
    )
    st.dataframe(monthly_table, use_container_width=True, hide_index=True)

    st.subheader("Complaint trend")
    if month_complaints.empty:
        st.info(f"No complaints recorded for {current_period_label}.")
        return
    reason_scope = complaints[complaints["Year"] == 2025].copy()
    reason_scope["Month"] = reason_scope["Date"].dt.to_period("M").astype(str)
    reason_order = sorted(reason_scope["Month"].unique())
    if metric == "Settlement total":
        reason_contribution = (reason_scope.groupby(["Reason", "Month"])["Settlement_Total"]
                               .sum().rename("Value").reset_index())
        reason_label = "Settlement total"
    else:
        reason_contribution = (reason_scope.groupby(["Reason", "Month"]).size()
                               .rename("PQR count").reset_index())
        if metric == "PQR rate":
            reason_batches = batches[batches["Year"] == 2025].copy()
            reason_batches["Month"] = reason_batches["Production_Date"].dt.to_period("M").astype(str)
            batch_counts = reason_batches.groupby("Month").size().rename("Batches")
            reason_contribution = reason_contribution.join(batch_counts, on="Month")
            reason_contribution["Value"] = reason_contribution["PQR count"].div(
                reason_contribution["Batches"].replace(0, pd.NA)
            ).fillna(0)
            reason_label = "PQR rate"
        else:
            reason_contribution["Value"] = reason_contribution["PQR count"]
            reason_label = "PQR count"
    complaint_fig = px.line(
        reason_contribution, x="Month", y="Value", color="Reason", markers=True,
        category_orders={"Month": reason_order},
        title=f"{metric} by reason over 2025",
        labels={"Value": reason_label},
    )
    complaint_fig.update_layout(height=500, coloraxis_showscale=False,
                                yaxis_title=reason_label, xaxis=dict(tickangle=-45))
    st.plotly_chart(complaint_fig, use_container_width=True)
    complaint_table = (reason_contribution.pivot_table(
        index="Reason", columns="Month", values="Value", aggfunc="sum", fill_value=0
    ).reindex(columns=reason_order, fill_value=0))
    complaint_table["Total"] = complaint_table.sum(axis=1)
    complaint_table = complaint_table.sort_values("Total", ascending=False)
    complaint_table = complaint_table.reset_index()
    table_columns = complaint_table.columns[1:]
    complaint_table[table_columns] = complaint_table[table_columns].map(
        lambda value: f"${value:,.2f}" if metric == "Settlement total"
        else f"{value:,.3f}" if metric == "PQR rate"
        else f"{value:,.0f}"
    )
    st.dataframe(complaint_table, use_container_width=True, hide_index=True)


render_overview_trends()

focus = None

def metric_by(complaint_rows: pd.DataFrame, batch_rows: pd.DataFrame, key: str) -> pd.Series:
    if metric == "PQR count":
        return complaint_rows.groupby(key).size().astype(float)
    if metric == "Settlement total":
        return complaint_rows.groupby(key)["Settlement_Total"].sum()
    out = pd.concat([complaint_rows.groupby(key).size().rename("PQR count"),
                     batch_rows.groupby(key).size().rename("Batches")], axis=1, sort=True)
    out = out[out["Batches"] > 0].fillna(0)
    return out["PQR count"] / out["Batches"]


def metric_by_batch_date(batch_rows: pd.DataFrame,
                         complaint_rows: pd.DataFrame | None = None) -> pd.Series:
    """Metric per production date, using complaints tied to batches made on that date."""
    if complaint_rows is None:
        complaint_rows = complaints
    linked = complaint_rows[complaint_rows["Batch_Number"].isin(batch_rows["Batch_Number"])].merge(
        batch_rows[["Batch_Number", "Production_Date"]], on="Batch_Number", how="left"
    )
    out = metric_by(linked, batch_rows, "Production_Date")
    out = out[out.index.isin(linked["Production_Date"])]
    out.index = out.index.strftime("%Y-%m-%d")
    return out


def top_worst(values: pd.Series, label: str) -> pd.DataFrame:
    out = values.sort_values(ascending=False).head(10).rename("Value")
    out.index.name = label
    return out.reset_index()


def change_by(key: str, label: str) -> pd.DataFrame:
    current = metric_by(month_complaints, month_batches, key)
    prior = metric_by(in_month(complaints, "Date", previous_period),
                      in_month(batches, "Production_Date", previous_period), key)
    change = pd.concat([current, prior], axis=1, keys=["current", "prior"])
    # Missing rate means no batches (undefined); missing count/settlement means zero.
    change = change.dropna() if metric == "PQR rate" else change.fillna(0)
    change = change["current"] - change["prior"]
    return top_worst(change[change > 0], label)


def worst_chart(frame: pd.DataFrame, label_column: str, value_label: str,
                chart_metric: str | None = None) -> None:
    if frame.empty:
        st.info("Nothing to show.")
        return
    chart_metric = chart_metric or metric
    text_format = {"PQR count": "%{x:,.0f}", "Settlement total": "$%{x:,.2f}"}.get(
        chart_metric, "%{x:.3f}")
    fig = px.bar(frame, x="Value", y=label_column, orientation="h",
                 color="Value", color_continuous_scale="Reds",
                 labels={"Value": value_label})
    fig.update_traces(texttemplate=text_format, textposition="outside", cliponaxis=False,
                      hovertemplate=f"%{{y}}<br>{value_label}: {text_format}<extra></extra>")
    fig.update_layout(height=420, coloraxis_showscale=False, margin=dict(t=10, r=60),
                      yaxis=dict(type="category", autorange="reversed", title=None))
    st.plotly_chart(fig, use_container_width=True)


def pqr_rate_by(complaint_rows: pd.DataFrame, batch_rows: pd.DataFrame,
                key: str) -> pd.Series:
    counts = complaint_rows.groupby(key).size().rename("Complaints")
    batch_counts = batch_rows.groupby(key).size().rename("Batches")
    rates = pd.concat([counts, batch_counts], axis=1).fillna(0)
    rates = rates[rates["Batches"] > 0]
    return rates["Complaints"] / rates["Batches"]


def rex_monthly_rates(rex_numbers: list[str]) -> pd.DataFrame:
    year_complaints = in_year(complaints, "Date", current_year)
    year_batches = in_year(batches, "Production_Date", current_year)
    periods = pd.period_range(f"{current_year}-01", f"{current_year}-12", freq="M")
    rows = []
    for rex_number in rex_numbers:
        rex_complaints = year_complaints[year_complaints["REX_Number"] == rex_number]
        rex_batches = year_batches[year_batches["REX_Number"] == rex_number]
        complaint_counts = rex_complaints.groupby(
            rex_complaints["Date"].dt.to_period("M")
        ).size()
        batch_counts = rex_batches.groupby(
            rex_batches["Production_Date"].dt.to_period("M")
        ).size()
        values = pd.concat([complaint_counts.rename("Complaints"),
                            batch_counts.rename("Batches")], axis=1).reindex(periods).fillna(0)
        values["PQR rate"] = values["Complaints"].div(values["Batches"].replace(0, pd.NA)).fillna(0)
        values["Period"] = values.index.astype(str)
        values["REX"] = rex_number
        rows.append(values[["Period", "REX", "PQR rate"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["Period", "REX", "PQR rate"]
    )


def render_rex_rate_trend(rex_numbers: list[str], title: str) -> None:
    trend = rex_monthly_rates(rex_numbers)
    if trend.empty:
        st.info("Nothing to show.")
        return
    fig = px.line(trend, x="Period", y="PQR rate", color="REX", markers=True,
                  title=title, labels={"Period": "Month"})
    fig.update_traces(hovertemplate="%{fullData.name}<br>PQR rate: %{y:.3f}<extra></extra>")
    fig.update_layout(height=420, xaxis_title="Month", yaxis_title="PQR rate")
    st.plotly_chart(fig, use_container_width=True)


def product_monthly_rates(product_families: list[str]) -> pd.DataFrame:
    year_complaints = in_year(complaints, "Date", current_year)
    year_batches = in_year(batches, "Production_Date", current_year)
    periods = pd.period_range(f"{current_year}-01", f"{current_year}-12", freq="M")
    rows = []
    for product_family in product_families:
        product_complaints = year_complaints[
            year_complaints["Product_Line"] == product_family
        ]
        product_batches = year_batches[year_batches["Product_Line"] == product_family]
        complaint_counts = product_complaints.groupby(
            product_complaints["Date"].dt.to_period("M")
        ).size()
        batch_counts = product_batches.groupby(
            product_batches["Production_Date"].dt.to_period("M")
        ).size()
        values = pd.concat([complaint_counts.rename("Complaints"),
                            batch_counts.rename("Batches")], axis=1).reindex(periods).fillna(0)
        values["PQR rate"] = values["Complaints"].div(
            values["Batches"].replace(0, pd.NA)
        ).fillna(0)
        values["Period"] = values.index.astype(str)
        values["Product family"] = product_family
        rows.append(values[["Period", "Product family", "PQR rate"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["Period", "Product family", "PQR rate"]
    )


def render_product_rate_trend(product_families: list[str], title: str) -> None:
    trend = product_monthly_rates(product_families)
    if trend.empty:
        st.info("Nothing to show.")
        return
    fig = px.line(trend, x="Period", y="PQR rate", color="Product family", markers=True,
                  title=title, labels={"Period": "Month"})
    fig.update_traces(hovertemplate="%{fullData.name}<br>PQR rate: %{y:.3f}<extra></extra>")
    fig.update_layout(height=420, xaxis_title="Month", yaxis_title="PQR rate")
    st.plotly_chart(fig, use_container_width=True)


with rex_tab:
    with st.container(border=True, key="rex-year-panel"):
        st.subheader(f"Highest PQR rate REXs · {current_year}")
        current_year_complaints = in_year(complaints, "Date", current_year)
        current_year_batches = in_year(batches, "Production_Date", current_year)
        current_year_rex = top_worst(
            pqr_rate_by(current_year_complaints, current_year_batches, "REX_Number"), "REX"
        )
        current_year_rex["REX"] = current_year_rex["REX"].astype(str)
        ranking_column, trend_column = st.columns(2)
        with ranking_column:
            worst_chart(current_year_rex, "REX", "PQR rate", chart_metric="PQR rate")
        with trend_column:
            render_rex_rate_trend(
                current_year_rex["REX"].tolist(),
                f"PQR rate by month · highest PQR rate REXs · {current_year}",
            )

    with st.container(border=True, key="rex-increase-panel"):
        st.subheader(
            f"Highest PQR rate increases by REX · {previous_period_label} to {current_period_label}"
        )
        current_rex_rates = pqr_rate_by(month_complaints, month_batches, "REX_Number")
        prior_rex_rates = pqr_rate_by(
            in_month(complaints, "Date", previous_period),
            in_month(batches, "Production_Date", previous_period),
            "REX_Number",
        )
        rex_rate_change = pd.concat(
            [current_rex_rates.rename("Current"), prior_rex_rates.rename("Previous")], axis=1
        ).dropna()
        rex_rate_change["Value"] = rex_rate_change["Current"] - rex_rate_change["Previous"]
        monthly_rex = rex_rate_change[rex_rate_change["Value"] > 0].sort_values(
            "Value", ascending=False
        ).head(6).reset_index(names="REX")
        monthly_rex["REX"] = monthly_rex["REX"].astype(str)
        increase_column, monthly_trend_column = st.columns(2)
        with increase_column:
            worst_chart(monthly_rex[["REX", "Value"]], "REX", "PQR rate increase",
                        chart_metric="PQR rate")
        with monthly_trend_column:
            render_rex_rate_trend(
                monthly_rex["REX"].tolist(),
                f"PQR rate by month · greatest increases from {previous_period_label} to {current_period_label}",
            )

    compare_panel = st.container(border=True, key="rex-compare-panel")
    compare_panel.__enter__()
    st.subheader("Compare PQR trends")
    comparison_start = min(complaints["Date"].min(), batches["Production_Date"].min())
    comparison_end = max(complaints["Date"].max(), batches["Production_Date"].max())
    rex_options = ["None"] + sorted(complaints["REX_Number"].dropna().unique().tolist())
    rex_comparison_columns = st.columns(2)
    rex_comparisons = []
    for selection_number, column in enumerate(rex_comparison_columns, start=1):
        with column:
            st.markdown(f"#### Selection {selection_number}")
            selected_rex = st.selectbox(
                "REX", rex_options, key=f"rex_comparison_value_{selection_number}"
            )
            selected_dates = st.slider(
                "Time frame",
                min_value=comparison_start.date(),
                max_value=comparison_end.date(),
                value=(comparison_start.date(), comparison_end.date()),
                format="MMM YYYY",
                key=f"rex_comparison_dates_{selection_number}",
            )
            rex_comparisons.append((selected_rex, selected_dates))

    rex_comparison_metric = st.selectbox(
        "Comparison metric",
        ["PQR count", "PQR rate", "Settlement total"],
        key="rex_comparison_metric",
    )
    rex_comparison_frames = []
    for selection_number, (selected_rex, selected_dates) in enumerate(rex_comparisons, start=1):
        if selected_rex == "None":
            continue
        complaint_scope = complaints[
            (complaints["REX_Number"] == selected_rex)
            & (complaints["Date"] >= pd.Timestamp(selected_dates[0]))
            & (complaints["Date"] < pd.Timestamp(selected_dates[1]) + pd.offsets.MonthBegin(1))
        ].copy()
        batch_scope = batches[
            (batches["REX_Number"] == selected_rex)
            & (batches["Production_Date"] >= pd.Timestamp(selected_dates[0]))
            & (batches["Production_Date"] < pd.Timestamp(selected_dates[1]) + pd.offsets.MonthBegin(1))
        ].copy()
        comparison_periods = pd.DataFrame({
            "Period": pd.period_range(selected_dates[0], selected_dates[1], freq="M").astype(str)
        })
        if rex_comparison_metric == "Settlement total":
            values = complaint_scope.groupby(complaint_scope["Date"].dt.to_period("M").astype(str))["Settlement_Total"].sum()
        else:
            complaint_counts = complaint_scope.groupby(
                complaint_scope["Date"].dt.to_period("M").astype(str)
            ).size()
            if rex_comparison_metric == "PQR rate":
                batch_counts = batch_scope.groupby(
                    batch_scope["Production_Date"].dt.to_period("M").astype(str)
                ).size()
                values = complaint_counts.div(batch_counts.replace(0, pd.NA)).fillna(0)
            else:
                values = complaint_counts
        frame = comparison_periods.copy()
        frame["Value"] = frame["Period"].map(values).fillna(0)
        frame["Selection"] = f"Selection {selection_number}: {selected_rex}"
        rex_comparison_frames.append(frame)

    if rex_comparison_frames:
        rex_comparison_trend = pd.concat(rex_comparison_frames, ignore_index=True)
        comparison_fig = px.line(
            rex_comparison_trend, x="Period", y="Value", color="Selection", markers=True,
            title=f"{rex_comparison_metric} by month",
            labels={"Value": rex_comparison_metric, "Period": "Month"},
        )
        comparison_fig.update_layout(height=420, xaxis_title="Month", yaxis_title=rex_comparison_metric)
        st.plotly_chart(comparison_fig, use_container_width=True)
        rex_comparison_table = rex_comparison_trend.pivot_table(
            index="Selection", columns="Period", values="Value", aggfunc="sum", fill_value=0
        ).sort_index(axis=1)
        rex_comparison_table["Total"] = rex_comparison_table.sum(axis=1)
        st.dataframe(rex_comparison_table.reset_index(), use_container_width=True, hide_index=True)
    else:
        st.info("Choose at least one REX to compare.")

    compare_panel.__exit__(None, None, None)

    stats_panel = st.container(border=True, key="rex-stats-panel")
    stats_panel.__enter__()
    st.subheader("Complaint stats comparison")
    reason_frames = []
    detail_frames = []
    for selection_number, (selected_rex, selected_dates) in enumerate(
            rex_comparisons, start=1):
        if selected_rex == "None":
            continue
        complaint_scope = complaints[
            (complaints["REX_Number"] == selected_rex)
            & (complaints["Date"] >= pd.Timestamp(selected_dates[0]))
            & (complaints["Date"] < pd.Timestamp(selected_dates[1])
               + pd.offsets.MonthBegin(1))
        ].copy()
        reason_counts = complaint_scope.groupby("Reason").size().rename(
            "Complaints"
        ).reset_index()
        if rex_comparison_metric == "Settlement total":
            reason_counts["Value"] = complaint_scope.groupby("Reason")["Settlement_Total"].sum().reindex(
                reason_counts["Reason"]
            ).to_numpy()
        elif rex_comparison_metric == "PQR rate":
            batch_count = len(batches[
                (batches["REX_Number"] == selected_rex)
                & (batches["Production_Date"] >= pd.Timestamp(selected_dates[0]))
                & (batches["Production_Date"] < pd.Timestamp(selected_dates[1])
                   + pd.offsets.MonthBegin(1))
            ])
            reason_counts["Value"] = reason_counts["Complaints"].div(batch_count).fillna(0)
        else:
            reason_counts["Value"] = reason_counts["Complaints"]
        reason_counts["Selection"] = f"Selection {selection_number}: {selected_rex}"
        reason_frames.append(reason_counts)
        detail_frames.append((f"Selection {selection_number}: {selected_rex}", complaint_scope))

    if reason_frames:
        reason_comparison = pd.concat(reason_frames, ignore_index=True)
        reason_order = (reason_comparison.groupby("Reason")["Value"].sum()
                        .sort_values(ascending=False).index.tolist())
        reason_fig = px.bar(
            reason_comparison, x="Reason", y="Value", color="Selection", barmode="group",
            title=f"{rex_comparison_metric} by complaint reason",
            labels={"Value": rex_comparison_metric},
            category_orders={"Reason": reason_order},
        )
        reason_fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(reason_fig, use_container_width=True)
    else:
        st.info("Choose a REX above to view complaint statistics.")

    stats_panel.__exit__(None, None, None)
    comments_panel = st.container(border=True, key="rex-comments-panel")
    comments_panel.__enter__()
    st.subheader("Complaint comments")
    if detail_frames:
        detail_columns = st.columns(2)
        for column, (label, detail) in zip(detail_columns, detail_frames):
            with column:
                st.markdown(f"#### {label}")
                st.caption(f"{len(detail):,} complaints")
                st.dataframe(
                    detail.sort_values("Date", ascending=False)[[
                        "Ticket_ID", "Date", "Time", "Comments", "Reason", "Settlement_Total",
                        "Batch_Number", "Product_Line", "Plant", "Region", "Channel",
                    ]],
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.info("Choose a REX above to view complaint comments.")
    comments_panel.__exit__(None, None, None)


with product_tab:
    with st.container(border=True, key="product-year-panel"):
        st.subheader(f"PQR rate by product family · {current_year}")
        current_year_complaints = in_year(complaints, "Date", current_year)
        current_year_batches = in_year(batches, "Production_Date", current_year)
        current_year_products = top_worst(
            pqr_rate_by(current_year_complaints, current_year_batches, "Product_Line"),
            "Product family",
        )
        current_year_products["Product family"] = current_year_products["Product family"].astype(str)
        ranking_column, trend_column = st.columns(2)
        with ranking_column:
            worst_chart(current_year_products, "Product family", "PQR rate",
                        chart_metric="PQR rate")
        with trend_column:
            render_product_rate_trend(
                current_year_products["Product family"].tolist(),
                f"PQR rate by month · product family · {current_year}",
            )

    with st.container(border=True, key="product-increase-panel"):
        st.subheader(
            "PQR rate increases by product family · "
            f"{previous_period_label} to {current_period_label}"
        )
        current_product_rates = pqr_rate_by(month_complaints, month_batches, "Product_Line")
        prior_product_rates = pqr_rate_by(
            in_month(complaints, "Date", previous_period),
            in_month(batches, "Production_Date", previous_period),
            "Product_Line",
        )
        product_rate_change = pd.concat(
            [current_product_rates.rename("Current"), prior_product_rates.rename("Previous")],
            axis=1,
        ).dropna()
        product_rate_change["Value"] = (
            product_rate_change["Current"] - product_rate_change["Previous"]
        )
        monthly_products = product_rate_change[product_rate_change["Value"] > 0].sort_values(
            "Value", ascending=False
        ).head(6).reset_index(names="Product family")
        monthly_products["Product family"] = monthly_products["Product family"].astype(str)
        increase_column, monthly_trend_column = st.columns(2)
        with increase_column:
            worst_chart(monthly_products[["Product family", "Value"]], "Product family",
                        "PQR rate increase", chart_metric="PQR rate")
        with monthly_trend_column:
            render_product_rate_trend(
                monthly_products["Product family"].tolist(),
                "PQR rate by month · increases from "
                f"{previous_period_label} to {current_period_label}",
            )

    product_compare_panel = st.container(border=True, key="product-compare-panel")
    product_compare_panel.__enter__()
    st.subheader("Compare PQR trends")
    comparison_start = min(complaints["Date"].min(), batches["Production_Date"].min())
    comparison_end = max(complaints["Date"].max(), batches["Production_Date"].max())
    product_options = ["None"] + sorted(complaints["Product_Line"].dropna().unique().tolist())
    product_comparison_columns = st.columns(2)
    product_comparisons = []
    for selection_number, column in enumerate(product_comparison_columns, start=1):
        with column:
            st.markdown(f"#### Selection {selection_number}")
            selected_product = st.selectbox(
                "Product family", product_options,
                key=f"product_comparison_value_{selection_number}",
            )
            selected_dates = st.slider(
                "Time frame",
                min_value=comparison_start.date(),
                max_value=comparison_end.date(),
                value=(comparison_start.date(), comparison_end.date()),
                format="MMM YYYY",
                key=f"product_comparison_dates_{selection_number}",
            )
            product_comparisons.append((selected_product, selected_dates))

    product_comparison_metric = st.selectbox(
        "Comparison metric",
        ["PQR count", "PQR rate", "Settlement total"],
        key="product_comparison_metric",
    )
    product_comparison_frames = []
    for selection_number, (selected_product, selected_dates) in enumerate(
            product_comparisons, start=1):
        if selected_product == "None":
            continue
        complaint_scope = complaints[
            (complaints["Product_Line"] == selected_product)
            & (complaints["Date"] >= pd.Timestamp(selected_dates[0]))
            & (complaints["Date"] < pd.Timestamp(selected_dates[1]) + pd.offsets.MonthBegin(1))
        ].copy()
        batch_scope = batches[
            (batches["Product_Line"] == selected_product)
            & (batches["Production_Date"] >= pd.Timestamp(selected_dates[0]))
            & (batches["Production_Date"] < pd.Timestamp(selected_dates[1])
               + pd.offsets.MonthBegin(1))
        ].copy()
        comparison_periods = pd.DataFrame({
            "Period": pd.period_range(selected_dates[0], selected_dates[1], freq="M").astype(str)
        })
        if product_comparison_metric == "Settlement total":
            values = complaint_scope.groupby(
                complaint_scope["Date"].dt.to_period("M").astype(str)
            )["Settlement_Total"].sum()
        else:
            complaint_counts = complaint_scope.groupby(
                complaint_scope["Date"].dt.to_period("M").astype(str)
            ).size()
            if product_comparison_metric == "PQR rate":
                batch_counts = batch_scope.groupby(
                    batch_scope["Production_Date"].dt.to_period("M").astype(str)
                ).size()
                values = complaint_counts.div(batch_counts.replace(0, pd.NA)).fillna(0)
            else:
                values = complaint_counts
        frame = comparison_periods.copy()
        frame["Value"] = frame["Period"].map(values).fillna(0)
        frame["Selection"] = f"Selection {selection_number}: {selected_product}"
        product_comparison_frames.append(frame)

    if product_comparison_frames:
        product_comparison_trend = pd.concat(product_comparison_frames, ignore_index=True)
        comparison_fig = px.line(
            product_comparison_trend, x="Period", y="Value", color="Selection", markers=True,
            title=f"{product_comparison_metric} by month",
            labels={"Value": product_comparison_metric, "Period": "Month"},
        )
        comparison_fig.update_layout(height=420, xaxis_title="Month",
                                     yaxis_title=product_comparison_metric)
        st.plotly_chart(comparison_fig, use_container_width=True)
        product_comparison_table = product_comparison_trend.pivot_table(
            index="Selection", columns="Period", values="Value", aggfunc="sum", fill_value=0
        ).sort_index(axis=1)
        product_comparison_table["Total"] = product_comparison_table.sum(axis=1)
        st.dataframe(product_comparison_table.reset_index(), use_container_width=True,
                     hide_index=True)
    else:
        st.info("Choose at least one product family to compare.")
    product_compare_panel.__exit__(None, None, None)

    product_stats_panel = st.container(border=True, key="product-stats-panel")
    product_stats_panel.__enter__()
    st.subheader("Complaint stats comparison")
    product_reason_frames = []
    product_detail_frames = []
    for selection_number, (selected_product, selected_dates) in enumerate(
            product_comparisons, start=1):
        if selected_product == "None":
            continue
        complaint_scope = complaints[
            (complaints["Product_Line"] == selected_product)
            & (complaints["Date"] >= pd.Timestamp(selected_dates[0]))
            & (complaints["Date"] < pd.Timestamp(selected_dates[1])
               + pd.offsets.MonthBegin(1))
        ].copy()
        reason_counts = complaint_scope.groupby("Reason").size().rename(
            "Complaints"
        ).reset_index()
        if product_comparison_metric == "Settlement total":
            reason_counts["Value"] = complaint_scope.groupby("Reason")["Settlement_Total"].sum().reindex(
                reason_counts["Reason"]
            ).to_numpy()
        elif product_comparison_metric == "PQR rate":
            batch_count = len(batches[
                (batches["Product_Line"] == selected_product)
                & (batches["Production_Date"] >= pd.Timestamp(selected_dates[0]))
                & (batches["Production_Date"] < pd.Timestamp(selected_dates[1])
                   + pd.offsets.MonthBegin(1))
            ])
            reason_counts["Value"] = reason_counts["Complaints"].div(batch_count).fillna(0)
        else:
            reason_counts["Value"] = reason_counts["Complaints"]
        reason_counts["Selection"] = f"Selection {selection_number}: {selected_product}"
        product_reason_frames.append(reason_counts)
        product_detail_frames.append(
            (f"Selection {selection_number}: {selected_product}", complaint_scope)
        )

    if product_reason_frames:
        product_reason_comparison = pd.concat(product_reason_frames, ignore_index=True)
        product_reason_order = (product_reason_comparison.groupby("Reason")["Value"].sum()
                                .sort_values(ascending=False).index.tolist())
        reason_fig = px.bar(
            product_reason_comparison, x="Reason", y="Value", color="Selection", barmode="group",
            title=f"{product_comparison_metric} by complaint reason",
            labels={"Value": product_comparison_metric},
            category_orders={"Reason": product_reason_order},
        )
        reason_fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(reason_fig, use_container_width=True)
    else:
        st.info("Choose a product family above to view complaint statistics.")
    product_stats_panel.__exit__(None, None, None)

    product_comments_panel = st.container(border=True, key="product-comments-panel")
    product_comments_panel.__enter__()
    st.subheader("Complaint comments")
    if product_detail_frames:
        detail_columns = st.columns(2)
        for column, (label, detail) in zip(detail_columns, product_detail_frames):
            with column:
                st.markdown(f"#### {label}")
                st.caption(f"{len(detail):,} complaints")
                st.dataframe(
                    detail.sort_values("Date", ascending=False)[[
                        "Ticket_ID", "Date", "Time", "Comments", "Reason", "Settlement_Total",
                        "Batch_Number", "Product_Line", "Plant", "Region", "Channel",
                    ]],
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.info("Choose a product family above to view complaint comments.")
    product_comments_panel.__exit__(None, None, None)


if focus is None:
    pass
elif focus.startswith("year:"):
    choice = focus.split(":", 1)[1]
    year_complaints = in_year(complaints, "Date", current_year)
    year_batches = in_year(batches, "Production_Date", current_year)
    st.markdown(f"**{choice} by {metric} · {current_year}**")
    if choice == "Top worst REX":
        worst_chart(top_worst(metric_by(year_complaints, year_batches, "REX_Number"), "REX"),
                    "REX", metric)
    elif choice == "Top worst batch date":
        worst_chart(top_worst(metric_by_batch_date(year_batches), "Batch date"),
                    "Batch date", metric)
    else:
        worst_chart(top_worst(metric_by(year_complaints, year_batches, "Product_Line"),
                              "Product family"), "Product family", metric)
elif focus.startswith("month:"):
    choice = focus.split(":", 1)[1]
    change_label = f"{metric} change vs {previous_period_label}"
    st.markdown(f"**{choice} · {current_period_label}**")
    if choice == "Top worst REX":
        st.caption(f"Largest {metric} increase vs {previous_period_label}")
        worst_chart(change_by("REX_Number", "REX"), "REX", change_label)
    elif choice == "Top worst batch date":
        st.caption(f"Highest {metric} by batch date · complaints received in "
                   f"{current_period_label}")
        worst_chart(top_worst(metric_by_batch_date(batches, month_complaints), "Batch date"),
                    "Batch date", metric)
    else:
        st.caption(f"Largest {metric} increase vs {previous_period_label}")
        worst_chart(change_by("Product_Line", "Product family"), "Product family", change_label)
elif focus == "year":
    if metric == "PQR count":
        year_metric = complaints.groupby("Year").size().rename("Value").reset_index()
        value_label = "PQR count"
        text_format = "%{text:,}"
    elif metric == "PQR rate":
        year_metric = (complaints.groupby("Year").size().rename("PQR count")
                       .to_frame().join(batches.groupby("Year").size().rename("Batches"))
                       .fillna(0).reset_index())
        year_metric["Value"] = year_metric["PQR count"].div(
            year_metric["Batches"].replace(0, pd.NA)
        ).fillna(0)
        value_label = "PQR rate"
        text_format = "%{text:.3f}"
    else:
        year_metric = (complaints.groupby("Year")["Settlement_Total"]
                       .sum().rename("Value").reset_index())
        value_label = "Settlement total"
        text_format = "$%{text:,.2f}"

    if metric == "PQR rate":
        year_fig = px.line(year_metric, x="Year", y="Value", text="Value", markers=True,
                           title=f"{metric} by year", labels={"Value": value_label})
        year_fig.update_traces(texttemplate=text_format, textposition="top center")
    else:
        year_fig = px.bar(year_metric, x="Year", y="Value", text="Value",
                          title=f"{metric} by year", labels={"Value": value_label})
        year_fig.update_traces(texttemplate=text_format, textposition="outside")
    year_fig.update_layout(height=380, xaxis=dict(type="category"))
    st.plotly_chart(year_fig, use_container_width=True)
elif focus == "month":
    scope_years = years
    scoped_complaints = complaints[complaints["Year"].isin(scope_years)].copy()
    scoped_batches = batches[batches["Year"].isin(scope_years)].copy()
    scoped_complaints["Month"] = scoped_complaints["Date"].dt.month
    scoped_batches["Month"] = scoped_batches["Production_Date"].dt.month
    monthly_grid = pd.MultiIndex.from_product(
        [scope_years, range(1, 13)], names=["Year", "Month"]
    ).to_frame(index=False)

    if metric == "PQR count":
        monthly_count = (scoped_complaints.groupby(["Year", "Month"]).size()
                         .rename("Value").reset_index())
        value_label = "PQR count"
        text_format = "%{text:,}"
    elif metric == "PQR rate":
        monthly_count = (scoped_complaints.groupby(["Year", "Month"]).size().rename("PQR count")
                         .to_frame()
                         .join(scoped_batches.groupby(["Year", "Month"]).size().rename("Batches"))
                         .fillna(0).reset_index())
        monthly_count["Value"] = monthly_count["PQR count"].div(
            monthly_count["Batches"].replace(0, pd.NA)
        ).fillna(0)
        value_label = "PQR rate"
        text_format = "%{text:.3f}"
    else:
        monthly_count = (scoped_complaints.groupby(["Year", "Month"])["Settlement_Total"]
                         .sum().rename("Value").reset_index())
        value_label = "Settlement total"
        text_format = "$%{text:,.2f}"

    monthly_count = (monthly_count.merge(monthly_grid, on=["Year", "Month"], how="right")
                     .merge(month_names, on="Month", how="left"))
    monthly_count["Value"] = monthly_count["Value"].fillna(0)
    monthly_count["Year"] = monthly_count["Year"].astype(str)

    count_fig = px.line(monthly_count, x="Month name", y="Value", color="Year", text="Value",
                        markers=True, category_orders={"Month name": month_order},
                        title=f"{metric} by month")
    count_fig.update_traces(texttemplate=text_format, textposition="top center")
    count_fig.update_layout(height=400, xaxis_title="Month", yaxis_title=value_label)
    st.plotly_chart(count_fig, use_container_width=True)

    monthly_table = (monthly_count.pivot(index="Year", columns="Month name", values="Value")
                     .reindex(columns=month_order, fill_value=0)
                     .fillna(0))
    monthly_table["Total"] = monthly_table.sum(axis=1)
    total_row = monthly_table.sum(axis=0).to_frame().T
    total_row.index = ["Total"]
    monthly_table = pd.concat([monthly_table, total_row])
    monthly_table.index.name = "Year"
    monthly_table = monthly_table.reset_index()
    monthly_table["Year"] = monthly_table["Year"].astype(str)
    numeric_columns = monthly_table.columns[1:]
    if metric == "PQR count":
        monthly_table[numeric_columns] = monthly_table[numeric_columns].round().astype(int)
    elif metric == "Settlement total":
        monthly_table[numeric_columns] = monthly_table[numeric_columns].map(
            lambda value: f"${value:,.2f}"
        )
    else:
        monthly_table[numeric_columns] = monthly_table[numeric_columns].map(
            lambda value: f"{value:,.3f}"
        )
    st.dataframe(monthly_table, use_container_width=True)
else:
    if month_complaints.empty:
        st.info(f"No complaints recorded for {current_period_label}.")
    else:
        month_batch_count = len(month_batches)
        if metric == "PQR count":
            reason_scope = complaints[
                complaints["Date"].dt.to_period("M").isin([previous_period, current_period])
            ].copy()
            reason_scope["Month"] = reason_scope["Date"].dt.strftime("%b %Y")
            reason_contribution = (reason_scope.groupby(["Reason", "Month"])
                                   .size().rename("Value").reset_index())
            reason_value_label = "PQR count"
            reason_text_format = "%{text:,}"
            reason_fig = px.bar(
                reason_contribution, x="Reason", y="Value", text="Value", color="Month",
                barmode="group", category_orders={
                    "Month": [previous_period.strftime("%b %Y"), current_period_label]
                }, title=f"PQR count by reason · {previous_period_label} and {current_period_label}",
                labels={"Value": reason_value_label},
            )
        else:
            if metric == "Settlement total":
                reason_contribution = (month_complaints.groupby("Reason")["Settlement_Total"]
                                       .sum().rename("Value").reset_index())
                reason_value_label = "Settlement total"
                reason_text_format = "$%{text:,.2f}"
            else:
                reason_contribution = (month_complaints.groupby("Reason").size()
                                       .rename("Value").reset_index())
                reason_contribution["Value"] = (
                    reason_contribution["Value"] / month_batch_count if month_batch_count else 0
                )
                reason_value_label = "PQR rate"
                reason_text_format = "%{text:.3f}"
            reason_contribution = reason_contribution.sort_values("Value", ascending=False)
            reason_fig = px.bar(reason_contribution, x="Reason", y="Value",
                                text="Value", title=f"{metric} by reason · {current_period_label}",
                                color="Value", color_continuous_scale="Reds",
                                labels={"Value": reason_value_label})
        category_fig = reason_fig
        category_fig.update_traces(texttemplate=reason_text_format, textposition="outside")
        category_fig.update_layout(height=500, coloraxis_showscale=False,
                                   yaxis_title=reason_value_label,
                                   xaxis=dict(tickangle=-45))
        st.plotly_chart(category_fig, use_container_width=True)

if "active_analysis_section" not in st.session_state:
    st.session_state["active_analysis_section"] = None

dive_records = complaints.merge(
    batches[["Batch_Number", "Production_Date"]], on="Batch_Number", how="left"
)
dive_records["REX"] = dive_records["REX_Number"]
dive_records["Batch"] = dive_records["Batch_Number"]
dive_records["Batch date"] = dive_records["Production_Date"].dt.strftime("%Y-%m-%d")
dive_records["Product family"] = dive_records["Product_Line"]
dive_records["Period"] = dive_records["Date"].dt.to_period("M").astype(str)

dive_batches = batches.copy()
dive_batches["REX"] = dive_batches["REX_Number"]
dive_batches["Batch"] = dive_batches["Batch_Number"]
dive_batches["Batch date"] = dive_batches["Production_Date"].dt.strftime("%Y-%m-%d")
dive_batches["Product family"] = dive_batches["Product_Line"]
dive_batches["Period"] = dive_batches["Production_Date"].dt.to_period("M").astype(str)

comparison_records = dive_records.copy()
comparison_batches = dive_batches.copy()


def format_comment_table(records: pd.DataFrame) -> pd.DataFrame:
    table = records.sort_values("Date", ascending=False).copy()
    table["Year"] = table["Date"].dt.year
    table["Month"] = table["Date"].dt.strftime("%b")
    table["Day"] = table["Date"].dt.day
    return table[[
        "Ticket_ID", "Year", "Month", "Day", "Time", "Comments", "Reason",
        "Settlement_Total", "REX", "Batch", "Batch date", "Product family",
        "Plant", "Region", "Channel",
    ]].rename(columns={
        "Ticket_ID": "Ticket",
        "Settlement_Total": "Settlement",
    })


def red_total_row_style(frame: pd.DataFrame) -> pd.DataFrame:
    totals = pd.to_numeric(
        frame["Total"].astype(str).str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce",
    )
    minimum = totals.min()
    maximum = totals.max()
    span = maximum - minimum or 1
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    for index, value in totals.items():
        intensity = (value - minimum) / span if pd.notna(value) else 0
        red = int(255 - 85 * intensity)
        green = int(245 - 125 * intensity)
        blue = int(245 - 125 * intensity)
        styles.loc[index, :] = f"background-color: rgb({red}, {green}, {blue})"
    return styles


def arrow_cell_style(text: str) -> str:
    marker = str(text)
    if marker.startswith("▲"):
        color = "#e8f5e9"
    elif marker.startswith("▼"):
        color = "#ffebee"
    else:
        color = ""
    return f"background-color: {color}" if color else ""


def render_explore_section(key_prefix: str = "") -> None:
    st.subheader("Explore PQR trends by REX, product, or batch date")
    top_columns = st.columns(3)
    dive_year = top_columns[0].selectbox(
        "Year", years, index=len(years) - 1, key=f"{key_prefix}dive_year"
    )
    dive_metric = top_columns[1].selectbox(
        "Metric", ["PQR count", "PQR rate", "Settlement total"],
        key=f"{key_prefix}dive_metric"
    )
    color_dimension = top_columns[2].selectbox(
        "Split chart by", ["None", "REX", "Batch date", "Product family"],
        key=f"{key_prefix}dive_color"
    )

    scoped_records = dive_records[dive_records["Year"] == dive_year]
    scoped_batches = dive_batches[dive_batches["Year"] == dive_year]
    filter_columns = st.columns(3)
    dive_filters = {}
    for column, dimension in zip(filter_columns, ["REX", "Batch date", "Product family"]):
        options = sorted(scoped_records[dimension].dropna().unique().tolist())
        dive_filters[dimension] = column.multiselect(
            dimension, options, key=f"{key_prefix}dive_filter_{dimension}",
            placeholder=f"All {dimension.lower()}s",
        )
    for dimension, values in dive_filters.items():
        if values:
            scoped_records = scoped_records[scoped_records[dimension].isin(values)]
            scoped_batches = scoped_batches[scoped_batches[dimension].isin(values)]

    if scoped_records.empty:
        st.info("No complaints match the selected filters.")
        return

    if dive_metric == "Settlement total":
        trend = (scoped_records.groupby(["Period"] if color_dimension == "None"
                                        else ["Period", color_dimension])["Settlement_Total"]
                 .sum().rename("Value").reset_index())
        value_label = "Settlement total"
        text_format = "$%{text:,.2f}"
    else:
        group_keys = ["Period"] if color_dimension == "None" else ["Period", color_dimension]
        trend = scoped_records.groupby(group_keys).size().rename("PQR count").reset_index()
        if dive_metric == "PQR rate":
            batch_counts = scoped_batches.groupby(group_keys).size().rename("Batches").reset_index()
            trend = trend.merge(batch_counts, on=group_keys, how="left")
            trend["Value"] = trend["PQR count"].div(
                trend["Batches"].replace(0, pd.NA)
            ).fillna(0)
            value_label = "PQR rate"
            text_format = "%{text:.3f}"
        else:
            trend = trend.rename(columns={"PQR count": "Value"})
            value_label = "PQR count"
            text_format = "%{text:,}"

    trend = trend.sort_values("Period")
    trend_fig = px.line(
        trend, x="Period", y="Value", markers=True,
        color=None if color_dimension == "None" else color_dimension,
        title=f"{dive_metric} by month",
        labels={"Value": value_label, "Period": "Month"},
    )
    trend_fig.update_traces(text=trend["Value"], texttemplate=text_format,
                            textposition="top center")
    trend_fig.update_layout(height=430, yaxis_title=value_label, xaxis_title="Month")
    st.plotly_chart(trend_fig, use_container_width=True)

    if color_dimension == "None":
        trend_table = trend.set_index("Period")[["Value"]].T
        trend_table.index = [value_label]
    else:
        trend_table = trend.pivot_table(index=color_dimension, columns="Period",
                                         values="Value", aggfunc="sum", fill_value=0)
    trend_table["Total"] = trend_table.sum(axis=1)
    trend_table = trend_table.sort_values("Total", ascending=False)
    batch_date_explore = color_dimension == "Batch date"
    chronological = sorted(trend["Period"].unique())
    change_column = None
    change_values = None
    if len(chronological) > 1 and not batch_date_explore:
        prior_period, latest_period = chronological[-2:]
        change_column = f"{latest_period} vs {prior_period}"
        change_values = trend_table[latest_period] - trend_table[prior_period]
    if dive_metric == "PQR count":
        value_columns = trend_table.columns
        trend_table[value_columns] = trend_table[value_columns].round().astype(int)
        format_change = lambda value: f"{value:,.0f}"
    elif dive_metric == "Settlement total":
        value_columns = trend_table.columns
        trend_table[value_columns] = trend_table[value_columns].map(
            lambda value: f"${value:,.2f}"
        )
        format_change = lambda value: f"${value:,.2f}"
    else:
        value_columns = trend_table.columns
        trend_table[value_columns] = trend_table[value_columns].map(
            lambda value: f"{value:,.3f}"
        )
        format_change = lambda value: f"{value:,.3f}"
    if change_column is not None:
        trend_table[change_column] = change_values.map(
            lambda value: f"{'▲' if value > 0 else '▼' if value < 0 else '▬'} "
                          f"{format_change(abs(value))}"
        )
    display_trend = trend_table.reset_index()
    if batch_date_explore:
        display_trend = display_trend.style.apply(red_total_row_style, axis=None)
        st.dataframe(display_trend, use_container_width=True, hide_index=True)
    elif change_column is not None:
        styled_trend = display_trend.style.map(
            arrow_cell_style, subset=[change_column]
        )
        st.dataframe(styled_trend, use_container_width=True, hide_index=True)
    else:
        st.dataframe(display_trend, use_container_width=True, hide_index=True)

    st.session_state[f"{key_prefix}show_explore_details"] = True
    if st.session_state[f"{key_prefix}show_explore_details"]:
        st.subheader("Complaint stats comparison")
        reason_counts = (scoped_records.groupby("Reason").size()
                         .rename("Complaints").reset_index())
        if dive_metric == "Settlement total":
            reason_counts["Value"] = (scoped_records.groupby("Reason")["Settlement_Total"]
                                       .sum().reindex(reason_counts["Reason"]).to_numpy())
        elif dive_metric == "PQR rate":
            reason_counts["Value"] = (
                reason_counts["Complaints"] / len(scoped_batches)
                if len(scoped_batches) else 0
            )
        else:
            reason_counts["Value"] = reason_counts["Complaints"]
        reason_counts = reason_counts.sort_values("Value", ascending=False)
        reason_counts["Percent"] = (
            reason_counts["Complaints"] / len(scoped_records) * 100
        )
        if dive_metric == "PQR count":
            reason_label_column = "Percent"
            reason_label_format = "%{text:.1f}%"
        elif dive_metric == "PQR rate":
            reason_label_column = "Value"
            reason_label_format = "%{text:.3f}"
        else:
            reason_label_column = "Value"
            reason_label_format = "$%{text:,.2f}"
        reason_fig = px.bar(
            reason_counts,
            x="Reason",
            y="Value",
            text=reason_label_column,
            title=f"{dive_metric} by complaint reason",
            labels={"Value": value_label},
            category_orders={"Reason": reason_counts["Reason"].tolist()},
        )
        reason_fig.update_traces(texttemplate=reason_label_format,
                                 textposition="outside", cliponaxis=False)
        reason_fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(reason_fig, use_container_width=True)

        st.subheader("Complaint comments")
        comment_table = format_comment_table(scoped_records)
        with st.container(height=430, border=True):
            st.dataframe(comment_table, use_container_width=True, hide_index=True)


with all_trends_tab:
    render_explore_section("all_trends_")

if st.session_state["active_analysis_section"] is None:
    st.stop()

if st.session_state["active_analysis_section"] == "explore":
    render_explore_section()
    st.stop()

st.subheader("Compare PQR trends")
st.caption("Compare two REXes, product families, or batch dates over selected years.")

comparison_dimensions = {
    "REX": "REX",
    "None": None,
    "Product family": "Product family",
    "Batch date": "Batch date",
}
available_start = min(
    comparison_records["Date"].min().to_period("M").to_timestamp(),
    comparison_batches["Production_Date"].min().to_period("M").to_timestamp(),
)
available_end = max(
    comparison_records["Date"].max().to_period("M").to_timestamp(),
    comparison_batches["Production_Date"].max().to_period("M").to_timestamp(),
)
default_start = max(available_start, available_end - pd.DateOffset(months=23))

selection_columns = st.columns(2)
comparison_selections = []
for index, column in enumerate(selection_columns, start=1):
    with column:
        st.markdown(f"#### Selection {index}")
        dimension_label = st.selectbox(
            "Compare by",
            list(comparison_dimensions),
            key=f"comparison_dimension_{index}",
        )
        dimension_column = comparison_dimensions[dimension_label]
        options = ["None"] if dimension_column is None else ["None"] + sorted(
            comparison_records[dimension_column].dropna().unique().tolist()
        )
        selected_option = st.selectbox(
            "Selection" if dimension_column is None else dimension_label,
            options,
            key=f"comparison_value_{index}",
        )
        selected_value = None if selected_option == "None" else selected_option
        selected_dates = st.slider(
            "Time frame",
            min_value=available_start.date(),
            max_value=available_end.date(),
            value=(default_start.date(), available_end.date()),
            format="MMM YYYY",
            key=f"comparison_year_{index}",
        )
        comparison_selections.append(
            {
                "label": (f"{dimension_label}: {selected_value or 'All'} "
                          f"({selected_dates[0]:%b %Y}-{selected_dates[1]:%b %Y})"),
                "dimension": dimension_column,
                "value": selected_value,
                "dates": selected_dates,
            }
        )

comparison_metric = st.selectbox(
    "Comparison metric",
    ["PQR count", "PQR rate", "Settlement total"],
    key="comparison_metric",
)


def comparison_scope(frame: pd.DataFrame, date_column: str, selection: dict) -> pd.DataFrame:
    mask = (
        (frame[date_column] >= pd.Timestamp(selection["dates"][0]))
        & (frame[date_column] < pd.Timestamp(selection["dates"][1])
           + pd.offsets.MonthBegin(1))
    )
    if selection["dimension"] is not None and selection["value"] is not None:
        mask &= frame[selection["dimension"]] == selection["value"]
    return frame[mask]

comparison_frames = []
for selection_number, selection in enumerate(comparison_selections, start=1):
    if selection["value"] is None:
        continue
    record_scope = comparison_scope(comparison_records, "Date", selection)
    batch_scope = comparison_scope(comparison_batches, "Production_Date", selection)
    comparison_periods = pd.DataFrame({
        "Period": pd.period_range(
            start=pd.Timestamp(selection["dates"][0]),
            end=pd.Timestamp(selection["dates"][1]),
            freq="M",
        ).astype(str)
    })
    if comparison_metric == "Settlement total":
        monthly_values = (record_scope.groupby("Period")["Settlement_Total"]
                          .sum().rename("Value").reset_index())
    else:
        monthly_values = record_scope.groupby("Period").size().rename("Complaints").reset_index()
        if comparison_metric == "PQR rate":
            monthly_batches = batch_scope.groupby("Period").size().rename("Batches").reset_index()
            monthly_values = monthly_values.merge(monthly_batches, on="Period", how="left")
            monthly_values["Value"] = monthly_values["Complaints"].div(
                monthly_values["Batches"].replace(0, pd.NA)
            ).fillna(0)
        else:
            monthly_values = monthly_values.rename(columns={"Complaints": "Value"})
    monthly_values = comparison_periods.merge(monthly_values, on="Period", how="left")
    monthly_values["Value"] = monthly_values["Value"].fillna(0)
    monthly_values["Selection"] = f"Selection {selection_number}"
    comparison_frames.append(monthly_values[["Period", "Value", "Selection"]])

if not comparison_frames:
    comparison_trend_fig = go.Figure()
    comparison_trend_fig.update_layout(
        title=f"{comparison_metric} by month",
        xaxis_title="Month",
        yaxis_title=comparison_metric,
    )
else:
    comparison_trend = pd.concat(comparison_frames, ignore_index=True)
    comparison_trend_fig = px.line(
        comparison_trend,
        x="Period",
        y="Value",
        color="Selection",
        markers=True,
        title=f"{comparison_metric} by month",
        labels={"Value": comparison_metric, "Period": "Month"},
        hover_data={"Value": ":,.3f" if comparison_metric == "PQR rate" else ":,.2f"},
    )
    if comparison_metric == "PQR count":
        comparison_trend_fig.update_traces(hovertemplate="%{y:,.0f}<extra></extra>")
    elif comparison_metric == "Settlement total":
        comparison_trend_fig.update_traces(hovertemplate="$%{y:,.2f}<extra></extra>")
    else:
        comparison_trend_fig.update_traces(hovertemplate="%{y:,.3f}<extra></extra>")
comparison_trend_fig.update_layout(height=420, yaxis_title=comparison_metric,
                                   xaxis_title="Month")
st.plotly_chart(comparison_trend_fig, use_container_width=True)

st.subheader("Comparison values")
if comparison_frames:
    comparison_table = (comparison_trend.pivot_table(
        index="Selection", columns="Period", values="Value", aggfunc="sum", fill_value=0
    ).sort_index(axis=1))
    comparison_table["Total"] = comparison_table.sum(axis=1)
    batch_date_comparison = any(
        selection["dimension"] == "Batch date" for selection in comparison_selections
    )
    product_family_comparison = any(
        selection["dimension"] == "Product family" for selection in comparison_selections
    )
    rex_comparison = any(
        selection["dimension"] == "REX" for selection in comparison_selections
    )
    periods = sorted(comparison_trend["Period"].unique())
    change_column = None
    if (len(periods) > 1 and not batch_date_comparison
            and not product_family_comparison and not rex_comparison):
        prior_period, latest_period = periods[-2:]
        change_column = f"{latest_period} vs {prior_period}"
        change_values = comparison_table[latest_period] - comparison_table[prior_period]
    value_columns = comparison_table.columns
    if comparison_metric == "PQR count":
        comparison_table[value_columns] = comparison_table[value_columns].round().astype(int)
        format_change = lambda value: f"{value:,.0f}"
    elif comparison_metric == "Settlement total":
        comparison_table[value_columns] = comparison_table[value_columns].map(
            lambda value: f"${value:,.2f}"
        )
        format_change = lambda value: f"${value:,.2f}"
    else:
        comparison_table[value_columns] = comparison_table[value_columns].map(
            lambda value: f"{value:,.3f}"
        )
        format_change = lambda value: f"{value:,.3f}"
    if change_column:
        comparison_table[change_column] = change_values.map(
            lambda value: f"{'▲' if value > 0 else '▼' if value < 0 else '▬'} "
                          f"{format_change(abs(value))}"
        )
    comparison_display = comparison_table.reset_index()
    if batch_date_comparison:
        comparison_display = comparison_display.style.apply(red_total_row_style, axis=None)
    elif change_column:
        comparison_display = comparison_display.style.map(
            arrow_cell_style, subset=[change_column]
        )
    st.dataframe(comparison_display, use_container_width=True, hide_index=True)
else:
    st.dataframe(pd.DataFrame(), use_container_width=True, hide_index=True)

if st.button("Look into complaint stats/comments for these selections", type="primary"):
    st.session_state["show_comparison_details"] = True

if st.session_state.get("show_comparison_details", False):
    st.divider()
    st.subheader("Complaint stats comparison")

    reason_frames = []
    detail_frames = []
    for selection_number, selection in enumerate(comparison_selections, start=1):
        detail_columns = [
            "Ticket_ID", "Date", "Time", "Comments", "Reason", "Settlement_Total",
            "REX", "Batch", "Batch date", "Product family", "Plant", "Region", "Channel",
        ]
        record_scope = comparison_scope(comparison_records, "Date", selection).copy()
        if selection["value"] is None:
            reason_counts = pd.DataFrame(columns=["Reason", "Complaints", "Value"])
            detail = record_scope.iloc[0:0][detail_columns].copy()
        else:
            batch_scope = comparison_scope(comparison_batches, "Production_Date", selection)
            reason_counts = (record_scope.groupby("Reason").size()
                             .rename("Complaints").reset_index())
            if comparison_metric == "Settlement total":
                reason_counts["Value"] = (record_scope.groupby("Reason")["Settlement_Total"]
                                           .sum().reindex(reason_counts["Reason"]).to_numpy())
            elif comparison_metric == "PQR rate":
                batch_count = len(batch_scope)
                reason_counts["Value"] = (
                    reason_counts["Complaints"] / batch_count if batch_count else 0
                )
            else:
                reason_counts["Value"] = reason_counts["Complaints"]
            detail = record_scope.sort_values("Date", ascending=False)[detail_columns].copy()
        
        reason_counts["Selection"] = f"Selection {selection_number}"
        reason_frames.append(reason_counts)
        detail["Selection"] = f"Selection {selection_number}"
        detail_frames.append(detail)

    reason_comparison = pd.concat(reason_frames, ignore_index=True)
    selection_totals = reason_comparison.groupby("Selection")["Complaints"].transform("sum")
    reason_comparison["Percent"] = (
        reason_comparison["Complaints"].div(selection_totals).mul(100).fillna(0)
    )
    if comparison_metric == "PQR count":
        reason_label_column = "Percent"
        reason_label_format = "%{text:.1f}%"
    elif comparison_metric == "PQR rate":
        reason_label_column = "Value"
        reason_label_format = "%{text:.3f}"
    else:
        reason_label_column = "Value"
        reason_label_format = "$%{text:,.2f}"
    if reason_comparison.empty:
        reason_fig = go.Figure()
        reason_fig.update_layout(title=f"{comparison_metric} by complaint reason")
    else:
        reason_fig = px.bar(
            reason_comparison,
            x="Reason",
            y="Value",
            text=reason_label_column,
            color="Selection",
            barmode="group",
            title=f"{comparison_metric} by complaint reason",
            labels={"Value": comparison_metric},
        )
    reason_fig.update_traces(texttemplate=reason_label_format, textposition="outside",
                             cliponaxis=False)
    reason_fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(reason_fig, use_container_width=True)

    detail_columns = st.columns(2)
    for column, selection_number, detail in zip(detail_columns, range(1, 3), detail_frames):
        with column:
            st.markdown(f"#### Selection {selection_number}")
            st.caption(f"{len(detail):,} complaints")
            display_detail = format_comment_table(detail)
            with st.container(height=430, border=True):
                st.dataframe(display_detail, use_container_width=True, hide_index=True)


