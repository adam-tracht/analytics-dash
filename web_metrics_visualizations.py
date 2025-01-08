# web_metrics_visualizations.py

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def display_web_metrics_overview(data, date_range=None):
    """Display key web metrics for the selected date range."""
    if date_range:
        filtered_data = data[
            (data['Week'].dt.date >= date_range[0]) &
            (data['Week'].dt.date <= date_range[1])
        ]
    else:
        filtered_data = data

    if filtered_data.empty:
        st.warning("No data available for the selected date range")
        return

    # Calculate aggregated metrics
    total_sessions = filtered_data['Sessions'].sum()
    total_transactions = filtered_data['Transactions'].sum()
    total_revenue = filtered_data['Purchase revenue'].sum()
    total_engaged = filtered_data['Engaged sessions'].sum()

    # Calculate overall metrics
    overall_cvr = (total_transactions / total_sessions * 100) if total_sessions > 0 else 0
    overall_bounce = ((total_sessions - total_engaged) / total_sessions * 100) if total_sessions > 0 else 0
    overall_aov = (total_revenue / total_transactions) if total_transactions > 0 else 0

    # Display metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Sessions", f"{total_sessions:,.0f}")

    with col2:
        st.metric("Total Transactions", f"{total_transactions:,.0f}")

    with col3:
        st.metric("Average Order Value", f"${overall_aov:,.2f}")

    with col4:
        st.metric("Conversion Rate", f"{overall_cvr:.2f}%")

    with col5:
        st.metric("Bounce Rate", f"{overall_bounce:.2f}%")

def create_web_metrics_trend(data, date_range=None):
    """Create a dual-axis line chart showing both total and filtered data for Sessions and CVR."""
    if date_range:
        filtered_data = data[
            (data['Week'].dt.date >= date_range[0]) &
            (data['Week'].dt.date <= date_range[1])
        ]
        show_filtered = True
    else:
        filtered_data = data
        show_filtered = False

    if filtered_data.empty:
        return None

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add total Sessions trace (dimmed)
    fig.add_trace(
        go.Scatter(
            x=data['Week'],
            y=data['Sessions'],
            name="Total Sessions",
            line=dict(color='rgba(200,200,200,0.5)', width=1),
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Total Sessions:</b> %{y:,.0f}<extra></extra>"
        ),
        secondary_y=False
    )

    # Add total CVR trace (dimmed)
    fig.add_trace(
        go.Scatter(
            x=data['Week'],
            y=data['Conversion Rate'],
            name="Total CVR",
            line=dict(color='rgba(200,200,200,0.5)', width=1),
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Total CVR:</b> %{y:.2f}%<extra></extra>"
        ),
        secondary_y=True
    )

    if show_filtered:
        # Add filtered Sessions trace
        fig.add_trace(
            go.Scatter(
                x=filtered_data['Week'],
                y=filtered_data['Sessions'],
                name="Filtered Sessions",
                line=dict(color="#4B90B0", width=2),
                hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                             "<b>Filtered Sessions:</b> %{y:,.0f}<extra></extra>"
            ),
            secondary_y=False
        )

        # Add filtered CVR trace
        fig.add_trace(
            go.Scatter(
                x=filtered_data['Week'],
                y=filtered_data['Conversion Rate'],
                name="Filtered CVR",
                line=dict(color="#FF6B6B", width=2),
                hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                             "<b>Filtered CVR:</b> %{y:.2f}%<extra></extra>"
            ),
            secondary_y=True
        )

    # Update layout
    fig.update_layout(
        title='Web Metrics Trends',
        template='plotly_white',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=100)
    )

    # Update axes
    fig.update_xaxes(title_text="Week", showgrid=True, gridcolor='rgba(211,211,211,0.3)')
    fig.update_yaxes(
        title_text="Sessions",
        secondary_y=False,
        showgrid=True,
        gridcolor='rgba(211,211,211,0.3)',
        tickformat=","
    )
    fig.update_yaxes(
        title_text="Conversion Rate (%)",
        secondary_y=True,
        showgrid=False,
        tickformat=".2f",
        ticksuffix="%"
    )

    return fig
