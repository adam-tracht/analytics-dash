# web_metrics_visualizations.py

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from date_filters import create_date_filter, filter_data_by_dates

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

def create_aov_transactions_trend(data, date_range=None):
    """Create a dual-axis line chart showing both total and filtered data for AOV and Transactions."""
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

    # Calculate AOV (Purchase revenue / Transactions)
    data['AOV'] = data['Purchase revenue'] / data['Transactions']
    filtered_data['AOV'] = filtered_data['Purchase revenue'] / filtered_data['Transactions']

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add total Transactions trace
    fig.add_trace(
        go.Scatter(
            x=data['Week'],
            y=data['Transactions'],
            name="Total Transactions",
            line=dict(color='#93C5FD', width=2),  # Light blue for unfiltered data
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Total Transactions:</b> %{y:,.0f}<extra></extra>"
        ),
        secondary_y=False
    )

    # Add total AOV trace
    fig.add_trace(
        go.Scatter(
            x=data['Week'],
            y=data['AOV'],
            name="Total AOV",
            line=dict(color='#FCA5A5', width=2),  # Light red for unfiltered data
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Total AOV:</b> $%{y:.2f}<extra></extra>"
        ),
        secondary_y=True
    )

    if show_filtered:
        # Add filtered Transactions trace
        fig.add_trace(
            go.Scatter(
                x=filtered_data['Week'],
                y=filtered_data['Transactions'],
                name="Filtered Transactions",
                line=dict(color="#60A5FA", width=3),  # Bright blue for better visibility
                hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                             "<b>Filtered Transactions:</b> %{y:,.0f}<extra></extra>"
            ),
            secondary_y=False
        )

        # Add filtered AOV trace
        fig.add_trace(
            go.Scatter(
                x=filtered_data['Week'],
                y=filtered_data['AOV'],
                name="Filtered AOV",
                line=dict(color="#F87171", width=3),  # Bright red for better visibility
                hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                             "<b>Filtered AOV:</b> $%{y:.2f}<extra></extra>"
            ),
            secondary_y=True
        )

    # Update layout
    fig.update_layout(
        title='Transactions and AOV Trends',
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
        margin=dict(t=100),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    # Update axes
    fig.update_xaxes(
        title_text="Week",
        showgrid=True,
        gridcolor='rgba(128,128,128,0.2)',
        gridwidth=1
    )
    fig.update_yaxes(
        title_text="Transactions",
        secondary_y=False,
        showgrid=True,
        gridcolor='rgba(128,128,128,0.2)',
        gridwidth=1,
        tickformat=","
    )
    fig.update_yaxes(
        title_text="Average Order Value ($)",
        secondary_y=True,
        showgrid=False,
        tickformat=".2f",
        tickprefix="$"
    )

    return fig

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

    # Add total Sessions trace (using a brighter color for better visibility)
    fig.add_trace(
        go.Scatter(
            x=data['Week'],
            y=data['Sessions'],
            name="Total Sessions",
            line=dict(color='#93C5FD', width=2),  # Light blue for unfiltered data
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Total Sessions:</b> %{y:,.0f}<extra></extra>"
        ),
        secondary_y=False
    )

    # Add total CVR trace
    fig.add_trace(
        go.Scatter(
            x=data['Week'],
            y=data['Conversion Rate'],
            name="Total CVR",
            line=dict(color='#FCA5A5', width=2),  # Light red for unfiltered data
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
                line=dict(color="#60A5FA", width=3),  # Bright blue for better visibility
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
                line=dict(color="#F87171", width=3),  # Bright red for better visibility
                hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                             "<b>Filtered CVR:</b> %{y:.2f}%<extra></extra>"
            ),
            secondary_y=True
        )

    # Update layout with improved grid visibility
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
        margin=dict(t=100),
        plot_bgcolor='rgba(0,0,0,0)',  # Transparent background
        paper_bgcolor='rgba(0,0,0,0)'  # Transparent paper
    )

    # Update axes with improved grid visibility
    fig.update_xaxes(
        title_text="Week",
        showgrid=True,
        gridcolor='rgba(128,128,128,0.2)',  # Brighter grid lines
        gridwidth=1
    )
    fig.update_yaxes(
        title_text="Sessions",
        secondary_y=False,
        showgrid=True,
        gridcolor='rgba(128,128,128,0.2)',  # Brighter grid lines
        gridwidth=1,
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

def display_web_metrics_dashboard(web_metrics_data, context_data=None):
    """
    Main function to display the web metrics dashboard with the consistent date filter.
    
    Args:
        web_metrics_data (pd.DataFrame): DataFrame containing web metrics
        context_data (pd.DataFrame, optional): DataFrame containing context information
    """
    if web_metrics_data is None:
        st.warning("No web metrics data available")
        return

    # Display context information if available
    if context_data is not None:
        with st.expander("📝 Data Context & Notes", expanded=False):
            for _, row in context_data.iterrows():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**{row['Category']}**")
                with col2:
                    st.markdown(row['Description'])
                    if pd.notna(row['Notes']):
                        st.caption(row['Notes'])

    # Use the consistent date filter component
    # Note: We need to rename 'Week' to 'Date' temporarily for the date filter component
    data_for_filter = web_metrics_data.rename(columns={'Week': 'Date'})
    start_date, end_date = create_date_filter(
        data_for_filter,
        view_type='Weekly',
        key_prefix='web_metrics'
    )

    # Display metrics overview
    st.subheader("📊 Web Metrics Overview")
    display_web_metrics_overview(web_metrics_data, (start_date, end_date))

    # Display trend charts
    st.subheader("📈 Web Metrics Trends")
    
    # Sessions and CVR trend
    trend_fig = create_web_metrics_trend(web_metrics_data, (start_date, end_date))
    if trend_fig:
        st.plotly_chart(trend_fig, use_container_width=True)
    
    # AOV and Transactions trend
    st.subheader("💰 Revenue Metrics Trends")
    aov_fig = create_aov_transactions_trend(web_metrics_data, (start_date, end_date))
    if aov_fig:
        st.plotly_chart(aov_fig, use_container_width=True)