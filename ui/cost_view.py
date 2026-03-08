import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from models.platform_state import PlatformState


def render():
    st.markdown("""
    <h2 style="color:#00d4ff;margin-bottom:4px;">Cost Estimation</h2>
    <p style="color:#718096;margin-bottom:20px;">Monthly and annual cloud infrastructure cost breakdown</p>
    """, unsafe_allow_html=True)

    state: PlatformState = st.session_state.get("platform_state", PlatformState())

    if not state.workflow_complete:
        st.info("Run the architecture workflow on the Dashboard page first.")
        return

    cost = state.cost_estimation
    if not cost:
        st.warning("Cost estimation data not available.")
        return

    # Top-level metrics
    total_monthly = cost.get("total_monthly", 0)
    total_annual = cost.get("total_annual", total_monthly * 12)
    provider = cost.get("provider", state.cloud_provider)
    region = cost.get("region", "us-east-1")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        _metric_card("Monthly Cost", f"${total_monthly:,.2f}", "#00d4ff")
    with m2:
        _metric_card("Annual Cost", f"${total_annual:,.0f}", "#9f7aea")
    with m3:
        _metric_card("Cloud Provider", provider, "#ff9900" if provider == "AWS" else "#34a853")
    with m4:
        _metric_card("Region", region, "#68d391")

    st.markdown("<br/>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        _render_line_items(cost)

    with col2:
        _render_category_chart(cost)

    st.markdown("<br/>", unsafe_allow_html=True)
    _render_savings(cost)


def _render_line_items(cost: dict):
    st.markdown("#### Cost Breakdown by Resource")
    items = cost.get("line_items", [])
    if not items:
        st.caption("No line items available.")
        return

    rows = []
    for item in items:
        rows.append({
            "Resource": item.get("resource", ""),
            "Type": item.get("type", ""),
            "Qty": str(item.get("qty", "")),
            "Unit Cost ($)": f"${item.get('unit_cost', 0):,.3f}",
            "Monthly ($)": item.get("monthly_cost", 0),
        })

    df = pd.DataFrame(rows)
    total = cost.get("subtotal", sum(i.get("monthly_cost", 0) for i in items))

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monthly ($)": st.column_config.NumberColumn(
                "Monthly ($)",
                format="$%.2f",
            )
        },
    )
    st.markdown(
        f'<div style="text-align:right;color:#00d4ff;font-size:14px;font-weight:800;'
        f'padding:6px 0;">Subtotal: ${total:,.2f} / month</div>',
        unsafe_allow_html=True,
    )


def _render_category_chart(cost: dict):
    st.markdown("#### Cost by Category")
    breakdown = cost.get("cost_breakdown_by_category", {})
    if not breakdown:
        return

    labels = list(breakdown.keys())
    values = list(breakdown.values())

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=["#00d4ff", "#9f7aea", "#68d391", "#f6ad55", "#fc8181", "#4299e1"]),
        textinfo="label+percent",
        textfont=dict(color="#e2e8f0", size=11),
    )])

    fig.update_layout(
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#e2e8f0"),
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        height=280,
        annotations=[dict(
            text=f"${sum(values):,.0f}",
            x=0.5, y=0.5,
            font=dict(size=18, color="#00d4ff", family="Arial Black"),
            showarrow=False,
        )],
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_savings(cost: dict):
    recommendations = cost.get("savings_recommendations", [])
    if not recommendations:
        return

    st.markdown("#### Cost Savings Opportunities")
    cols = st.columns(min(len(recommendations), 3))
    for i, rec in enumerate(recommendations[:3]):
        with cols[i]:
            st.markdown(
                f"""
                <div style="background:#1a2040;border:1px solid #2d3a6b;border-left:4px solid #9f7aea;
                            border-radius:8px;padding:14px;">
                    <div style="color:#9f7aea;font-size:11px;font-weight:700;margin-bottom:6px;">SAVINGS TIP</div>
                    <div style="color:#e2e8f0;font-size:13px;">{rec}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _metric_card(label: str, value: str, color: str):
    st.markdown(
        f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
                    padding:16px;text-align:center;border-top:3px solid {color};margin-bottom:8px;">
            <div style="color:{color};font-size:22px;font-weight:800;">{value}</div>
            <div style="color:#718096;font-size:11px;margin-top:4px;">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
