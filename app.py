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

st.set_page_config(page_title="PQR Dashboard", page_icon="🎨", layout="wide")


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

st.title("Paint Quality Report (PQR) Dashboard")

complaints["Year"] = complaints["Date"].dt.year
batches["Year"] = batches["Production_Date"].dt.year
years = sorted(set(complaints["Year"]).union(batches["Year"]))

metric = st.selectbox(
    "Metric",
    ["PQR count", "PQR rate", "Settlement total"],
    key="overview_metric",
)

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

st.subheader("PQR overview")
st.caption("Select a card to drive the charts below.")

month_names = pd.DataFrame({
    "Month": range(1, 13),
    "Month name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
})
month_order = month_names["Month name"].tolist()

focus = st.session_state.get("focus_card")
card_columns = st.columns(3)


def select_card(key: str) -> None:
    st.session_state["focus_card"] = None if st.session_state.get("focus_card") == key else key


def render_card(column, key: str, caption: str, label: str, value: str,
                delta: str | None, button_label: str) -> None:
    selected = focus == key
    with column:
        box = st.container(border=True)
        box.caption(caption)
        box.metric(label, value, delta=delta, delta_color="inverse")
        box.button("Hide chart" if selected else button_label, key=f"focus_{key}",
                   use_container_width=True,
                   type="primary" if selected else "secondary",
                   on_click=select_card, args=(key,))


render_card(
    card_columns[0], "year",
    f"Year to date · {current_year}", metric, format_value(year_value),
    delta_text(year_value, prior_year_value, str(previous_year)),
    "Show yearly chart",
)
render_card(
    card_columns[1], "month",
    f"Current month · {current_period_label}", metric, format_value(month_value),
    delta_text(month_value, prior_month_value, previous_period_label),
    "Show monthly chart",
)
render_card(
    card_columns[2], "reason",
    f"Top complaint · {current_period_label}",
    top_reason or "No complaints",
    format_value(top_reason_value) if top_reason else "—",
    delta_text(top_reason_value, prior_top_reason_value, previous_period_label)
    if top_reason else None,
    "Show complaint chart",
)

if focus is None:
    pass
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

    year_fig = px.bar(year_metric, x="Year", y="Value", text="Value",
                      title=f"{metric} by year", labels={"Value": value_label})
    year_fig.update_traces(texttemplate=text_format, textposition="outside")
    year_fig.update_layout(height=380, xaxis=dict(type="category"))
    st.plotly_chart(year_fig, use_container_width=True)
elif focus == "month":
    scope_years = [2025]
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

    count_fig = px.line(monthly_count, x="Month name", y="Value", color="Year",
                        markers=True, category_orders={"Month name": month_order},
                        title=f"{metric} by month")
    count_fig.update_traces(text=monthly_count["Value"], texttemplate=text_format,
                            textposition="top center")
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
        elif metric == "Settlement total":
            reason_contribution = (month_complaints.groupby("Reason")["Settlement_Total"]
                                   .sum().rename("Value").reset_index())
            reason_value_label = "Settlement total"
            reason_text_format = "$%{text:,.2f}"
        else:
            reason_contribution = (month_complaints.groupby("Reason").size()
                                   .rename("Value").reset_index())
            if metric == "PQR rate":
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

st.divider()
st.subheader("Explore and compare")
action_columns = st.columns(2)


def select_analysis_section(section: str) -> None:
    current_section = st.session_state.get("active_analysis_section")
    st.session_state["active_analysis_section"] = (
        None if current_section == section else section
    )


with action_columns[0]:
    st.button(
        "Hide PQR trends explorer" if st.session_state["active_analysis_section"] == "explore"
        else "Explore PQR trends by REX, product, or batch date",
        key="explore_analysis_section",
        use_container_width=True,
        type="primary" if st.session_state["active_analysis_section"] == "explore"
        else "secondary",
        on_click=select_analysis_section,
        args=("explore",),
    )
with action_columns[1]:
    st.button(
        "Hide PQR comparison/comments" if st.session_state["active_analysis_section"] == "compare"
        else "Compare PQR trends and review complaint stats and comments",
        key="compare_analysis_section",
        use_container_width=True,
        type="primary" if st.session_state["active_analysis_section"] == "compare"
        else "secondary",
        on_click=select_analysis_section,
        args=("compare",),
    )

if st.session_state["active_analysis_section"] is None:
    st.stop()

st.divider()

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


def render_explore_section() -> None:
    st.subheader("Explore PQR trends by REX, product, or batch date")
    top_columns = st.columns(3)
    dive_year = top_columns[0].selectbox(
        "Year", years, index=len(years) - 1, key="dive_year"
    )
    dive_metric = top_columns[1].selectbox(
        "Metric", ["PQR count", "PQR rate", "Settlement total"], key="dive_metric"
    )
    color_dimension = top_columns[2].selectbox(
        "Split chart by", ["None", "REX", "Batch date", "Product family"], key="dive_color"
    )

    scoped_records = dive_records[dive_records["Year"] == dive_year]
    scoped_batches = dive_batches[dive_batches["Year"] == dive_year]
    filter_columns = st.columns(3)
    dive_filters = {}
    for column, dimension in zip(filter_columns, ["REX", "Batch date", "Product family"]):
        options = sorted(scoped_records[dimension].dropna().unique().tolist())
        dive_filters[dimension] = column.multiselect(
            dimension, options, key=f"dive_filter_{dimension}",
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

    if st.button("Look into complaint stats/comments for this selection",
                 key="explore_complaint_stats", type="primary"):
        st.session_state["show_explore_details"] = True

    if st.session_state.get("show_explore_details", False):
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
        )
        reason_fig.update_traces(texttemplate=reason_label_format,
                                 textposition="outside", cliponaxis=False)
        reason_fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(reason_fig, use_container_width=True)

        st.subheader("Complaint comments")
        comment_table = format_comment_table(scoped_records)
        with st.container(height=430, border=True):
            st.dataframe(comment_table, use_container_width=True, hide_index=True)


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


