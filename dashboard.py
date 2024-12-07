# dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from data_loader import load_data_from_gsheet, filter_data
from visualizations import create_distribution_charts, create_pivot_analysis

def get_date_range(timeframe, data):
    """Get start and end dates based on selected timeframe."""
    end_date = data['Date'].max().date()
    
    if timeframe == '1W':
        start_date = end_date - timedelta(days=7)
    elif timeframe == '1M':
        start_date = end_date - timedelta(days=30)
    elif timeframe == '3M':
        start_date = end_date - timedelta(days=90)
    elif timeframe == '6M':
        start_date = end_date - timedelta(days=180)
    elif timeframe == '1Y':
        start_date = end_date - timedelta(days=365)
    else:  # Custom
        return None
    return start_date, end_date

def display_filters(data):
    """Display consolidated filters in a single row."""
    st.subheader("🎯 Filters")
    
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        retailer_filter = st.multiselect(
            "🏪 Retailers",
            options=["All"] + sorted(data['Retailer'].unique().tolist()),
            default="All"
        )
    
    with col2:
        product_filter = st.multiselect(
            "📦 Products",
            options=["All"] + sorted(data['Product Title'].unique().tolist()),
            default="All"
        )
    
    with col3:
        timeframe = st.selectbox(
            "📅 Time Range",
            options=['1W', '1M', '3M', '6M', '1Y', 'Custom'],
            index=1,  # Default to 1M
            format_func=lambda x: {
                '1W': 'Last Week',
                '1M': 'Last Month',
                '3M': 'Last 3 Months',
                '6M': 'Last 6 Months',
                '1Y': 'Last Year',
                'Custom': 'Custom Range'
            }[x]
        )
    
    with col4:
        if timeframe == 'Custom':
            date_range = st.date_input(
                "Select Dates",
                value=(data['Date'].min().date(), data['Date'].max().date()),
                min_value=data['Date'].min().date(),
                max_value=data['Date'].max().date()
            )
        else:
            date_range = get_date_range(timeframe, data)
    
    return retailer_filter, product_filter, date_range

def plot_sales_overview(data, filtered_data):
    """Create a compact sales overview chart showing both filtered and total data."""
    fig = go.Figure()
    
    # Add total sales line (light gray)
    total_sales = data.groupby('Date')['Sales Dollars'].sum().reset_index()
    fig.add_trace(go.Scatter(
        x=total_sales['Date'],
        y=total_sales['Sales Dollars'],
        mode='lines',
        name='Total Sales',
        line=dict(color='rgba(200,200,200,0.5)', width=1),
        hovertemplate="<b>Total Sales:</b> $%{y:,.2f}<br>"
    ))
    
    # Add filtered sales line
    filtered_sales = filtered_data.groupby('Date')['Sales Dollars'].sum().reset_index()
    fig.add_trace(go.Scatter(
        x=filtered_sales['Date'],
        y=filtered_sales['Sales Dollars'],
        mode='lines',
        name='Filtered Sales',
        line=dict(color='#4B90B0', width=2),
        hovertemplate="<b>Filtered Sales:</b> $%{y:,.2f}<br>"
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(t=30, b=30, l=60, r=30),
        xaxis=dict(title=None, showgrid=True, gridcolor='rgba(211,211,211,0.3)'),
        yaxis=dict(title=None, tickformat="$,.0f", gridcolor='rgba(211,211,211,0.3)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig

def create_sales_summary(data, dimension):
    """Create a summary DataFrame with both units and revenue."""
    summary = data.groupby(dimension).agg({
        'Sales Dollars': 'sum',
        'Units Sold': 'sum'
    }).reset_index()
    
    summary['Average Price'] = summary['Sales Dollars'] / summary['Units Sold']
    summary = summary.sort_values('Sales Dollars', ascending=False)
    
    # Calculate percentages
    summary['Revenue %'] = (summary['Sales Dollars'] / summary['Sales Dollars'].sum() * 100).round(1)
    summary['Units %'] = (summary['Units Sold'] / summary['Units Sold'].sum() * 100).round(1)
    
    return summary

def get_config_path():
    """Get the path to the configuration file."""
    config_dir = Path.home() / '.streamlit_sales_dashboard'
    config_dir.mkdir(exist_ok=True)
    return config_dir / 'config.json'

def load_saved_config():
    """Load saved configuration from file."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error loading saved configuration: {e}")
    return {}

def save_config(sheet_id, sheet_range):
    """Save configuration to file."""
    config_path = get_config_path()
    try:
        config = {
            'sheet_id': sheet_id,
            'sheet_range': sheet_range
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        st.warning(f"Error saving configuration: {e}")

def main():
    st.set_page_config(page_title="Sales Analytics Dashboard", layout="wide")
    st.title("📈 Sales Analytics Dashboard")
    
    # Initialize session state
    if 'sheet_id' not in st.session_state:
        config = load_saved_config()
        st.session_state.sheet_id = config.get('sheet_id', '')
        st.session_state.sheet_range = config.get('sheet_range', 'sales_template')

    # Sidebar configuration
    st.sidebar.header("📊 Data Source Configuration")
    st.sidebar.markdown("""
    ### How to connect your data:
    1. Share your Google Sheet with the service account email
    2. Enter the Sheet ID below (the string between /d/ and /edit in the URL)
    3. Specify the range (e.g., 'Sales Data!A1:H')
    """)
    
    sheet_id = st.sidebar.text_input("Google Sheet ID", value=st.session_state.sheet_id)
    sheet_range = st.sidebar.text_input(
        "Sheet Range", 
        value=st.session_state.sheet_range,
        help="Enter sheet name or include range (e.g. 'sales_template' or 'sales_template!A1:H')"
    )
    
    # Save/Clear configuration buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Save Config"):
            save_config(sheet_id, sheet_range)
            st.session_state.sheet_id = sheet_id
            st.session_state.sheet_range = sheet_range
            st.sidebar.success("Saved!")
    
    with col2:
        if st.button("Clear Config"):
            if os.path.exists(get_config_path()):
                os.remove(get_config_path())
            st.session_state.sheet_id = ''
            st.session_state.sheet_range = 'sales_template'
            st.sidebar.success("Cleared!")
            st.experimental_rerun()

    if not sheet_id:
        st.info("👈 Please enter your Google Sheet ID in the sidebar to get started.")
        return
    
    data, error = load_data_from_gsheet(sheet_id, sheet_range)
    if error:
        st.error(error)
        return
    if data is None:
        return
    
    # Display filters
    retailer_filter, product_filter, date_range = display_filters(data)
    
    # Apply filters
    filtered_data = filter_data(data, retailer_filter, product_filter, date_range)
    
    # Display sales overview
    st.plotly_chart(plot_sales_overview(data, filtered_data), use_container_width=True)
    
    # Add pivot analysis section
    create_pivot_analysis(filtered_data)
    
    # Display sales summaries in two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sales by Retailer")
        retailer_summary = create_sales_summary(filtered_data, 'Retailer')
        st.dataframe(
            retailer_summary.style.format({
                'Sales Dollars': '${:,.2f}',
                'Units Sold': '{:,}',
                'Average Price': '${:.2f}',
                'Revenue %': '{:.1f}%',
                'Units %': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    with col2:
        st.subheader("Sales by Product")
        product_summary = create_sales_summary(filtered_data, 'Product Title')
        st.dataframe(
            product_summary.style.format({
                'Sales Dollars': '${:,.2f}',
                'Units Sold': '{:,}',
                'Average Price': '${:.2f}',
                'Revenue %': '{:.1f}%',
                'Units %': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    # Combined Size and Color Analysis
    st.subheader("📊 Product Dimension Analysis")
    
    # Single product filter for both analyses
    product_filter = st.selectbox(
        "Select Product",
        options=["All"] + sorted(filtered_data['Product Title'].unique().tolist()),
        key="dimension_filter"
    )
    
    # Create tabs for Size and Color analysis
    dimension_tabs = st.tabs(["📏 Size Analysis", "🎨 Color Analysis"])
    
    with dimension_tabs[0]:  # Size Analysis
        size_line_fig, size_pie_fig = create_distribution_charts(filtered_data, 'Size', product_filter)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(size_line_fig, use_container_width=True)
        with col2:
            st.plotly_chart(size_pie_fig, use_container_width=True)
    
    with dimension_tabs[1]:  # Color Analysis
        color_line_fig, color_pie_fig = create_distribution_charts(filtered_data, 'Color', product_filter)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(color_line_fig, use_container_width=True)
        with col2:
            st.plotly_chart(color_pie_fig, use_container_width=True)

if __name__ == "__main__":
    main()