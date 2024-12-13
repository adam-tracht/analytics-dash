# dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta, date
from pathlib import Path
from data_loader import load_data_from_gsheet, filter_data, load_context_data
from visualizations import create_distribution_charts, create_pivot_analysis_with_comparison
import numpy as np

# Add constants at the top
DEMO_SHEET_ID = "1Ar7YABu7FIUAAAcq-8YZ6LRDVLh8DVV_cKN0WCU12kY"
DEMO_SHEET_RANGE = "sales_template"
TEMPLATE_LINK = "https://docs.google.com/spreadsheets/d/1Ar7YABu7FIUAAAcq-8YZ6LRDVLh8DVV_cKN0WCU12kY/edit#gid=0"

def display_context_section(context_data):
    """Display the context information in an expandable section."""
    with st.expander("📝 Data Context & Notes", expanded=False):
        if context_data is None:
            st.info("No context information available.")
            return
            
        # Display each category of information
        for _, row in context_data.iterrows():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"**{row['Category']}**")
            with col2:
                st.markdown(row['Description'])
                if pd.notna(row['Notes']):
                    st.caption(row['Notes'])

def get_date_range(timeframe, data):
    """Get start and end dates based on selected timeframe using complete periods."""
    # Get the actual data range
    min_date = data['Date'].min().date()
    max_date = data['Date'].max().date()
    
    # Return None for custom timeframe
    if timeframe == 'Custom':
        return None
    
    # Get today's date
    today = datetime.now().date()
    
    # Find the end of the last complete month (last day of previous month)
    last_complete_month = (today.replace(day=1) - timedelta(days=1))
    
    if timeframe == '1W':
        # Find the last complete week (Monday-Sunday)
        # Go back to the most recent Sunday
        days_since_sunday = today.weekday() + 1  # +1 because we want the previous Sunday
        last_sunday = today - timedelta(days=days_since_sunday)
        
        # Set the date range for the complete week
        end_date = last_sunday
        start_date = end_date - timedelta(days=6)  # Go back to Monday
        
        # Return both dates regardless of data availability
        return start_date, end_date
    else:
        # For all other periods, end at the last day of the previous month
        end_date = last_complete_month
        
        # Calculate start date based on timeframe
        if timeframe == '1M':
            # Start from first day of last complete month
            start_date = end_date.replace(day=1)
        elif timeframe == '3M':
            # Start from first day of 3 months before the last complete month
            year = end_date.year
            month = end_date.month - 2
            if month <= 0:
                year -= 1
                month = 12 + month
            start_date = date(year, month, 1)
        elif timeframe == '6M':
            # Start from first day of 6 months before the last complete month
            year = end_date.year
            month = end_date.month - 5
            if month <= 0:
                year -= 1
                month = 12 + month
            start_date = date(year, month, 1)
        elif timeframe == '1Y':
            # Start from first day of the same month last year
            start_date = date(end_date.year - 1, end_date.month, 1)
    
    # Ensure dates don't go beyond data boundaries for non-weekly periods
    if timeframe != '1W':
        start_date = max(start_date, min_date)
        end_date = min(end_date, max_date)
    
    return start_date, end_date

def display_filters(data):
    """Display consolidated filters in a single row with clear date range display."""
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
                '1W': 'Last Complete Week',
                '1M': 'Last Complete Month',
                '3M': 'Last 3 Complete Months',
                '6M': 'Last 6 Complete Months',
                '1Y': 'Last 12 Complete Months',
                'Custom': 'Custom Range'
            }[x]
        )
    
    with col4:
        st.write("Date Range:")
        if timeframe == 'Custom':
            date_range = st.date_input(
                "Select Dates",
                value=(data['Date'].min().date(), data['Date'].max().date()),
                min_value=data['Date'].min().date(),
                max_value=data['Date'].max().date(),
                label_visibility="collapsed"
            )
        else:
            date_range = get_date_range(timeframe, data)
            if date_range:
                # Add note for weekly data if the end date is beyond available data
                if timeframe == '1W' and date_range[1] > data['Date'].max().date():
                    st.write(f"{date_range[0].strftime('%Y-%m-%d')} to")
                    st.write(f"{date_range[1].strftime('%Y-%m-%d')}")
                    st.caption("⚠️ Data through end of week")
                else:
                    st.write(f"{date_range[0].strftime('%Y-%m-%d')} to")
                    st.write(f"{date_range[1].strftime('%Y-%m-%d')}")
    
    return retailer_filter, product_filter, date_range

def filter_data(data, retailer_filter, product_filter, date_range=None):
    """Filter data based on user selections, with optional date filtering."""
    filtered_data = data.copy()
    
    # Apply retailer and product filters
    if "All" not in retailer_filter:
        filtered_data = filtered_data[filtered_data['Retailer'].isin(retailer_filter)]
    if "All" not in product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(product_filter)]
    
    # Apply date filter only if provided
    if date_range is not None:
        filtered_data = filtered_data[
            (filtered_data['Date'].dt.date >= date_range[0]) &
            (filtered_data['Date'].dt.date <= date_range[1])
        ]
    
    return filtered_data

def plot_sales_overview(data, filtered_data, retailer_filter, product_filter):
    """Create a compact sales overview chart showing both filtered and total data."""
    fig = go.Figure()
    
    # Calculate total and filtered sales
    total_sales = data.groupby('Date')['Sales Dollars'].sum().reset_index()
    filtered_sales = filtered_data.groupby('Date')['Sales Dollars'].sum().reset_index()
    
    # Check if specific filters are applied (not "All")
    filters_applied = ("All" not in retailer_filter) or ("All" not in product_filter)
    
    # Add total sales line (light gray)
    fig.add_trace(go.Scatter(
        x=total_sales['Date'],
        y=total_sales['Sales Dollars'],
        mode='lines',
        name='Total Sales',
        line=dict(color='rgba(200,200,200,0.5)', width=1),
        hovertemplate="<b>Total Sales:</b> $%{y:,.2f}<br>",
        yaxis='y'
    ))
    
    # Add filtered sales line
    fig.add_trace(go.Scatter(
        x=filtered_sales['Date'],
        y=filtered_sales['Sales Dollars'],
        mode='lines',
        name='Filtered Sales',
        line=dict(color='#4B90B0', width=2),
        hovertemplate="<b>Filtered Sales:</b> $%{y:,.2f}<br>",
        yaxis='y2' if filters_applied else 'y'
    ))
    
    # Base layout settings
    layout = {
        'height': 300,
        'margin': dict(t=30, b=30, l=60, r=30),
        'xaxis': dict(
            title=None,
            showgrid=True,
            gridcolor='rgba(211,211,211,0.3)'
        ),
        'yaxis': dict(
            title='Sales',
            tickformat="$,.0f",
            gridcolor='rgba(211,211,211,0.3)',
            side='left'
        ),
        'legend': dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        'template': 'plotly_white',
        'hovermode': 'x unified'
    }
    
    # Add secondary y-axis only if specific filters are applied
    if filters_applied:
        layout.update({
            'margin': dict(t=30, b=30, l=60, r=60),
            'yaxis': dict(
                title='Total Sales',
                titlefont=dict(color='rgba(128,128,128,0.8)'),
                tickfont=dict(color='rgba(128,128,128,0.8)'),
                tickformat="$,.0f",
                gridcolor='rgba(211,211,211,0.3)',
                side='left'
            ),
            'yaxis2': dict(
                title='Filtered Sales',
                titlefont=dict(color='#4B90B0'),
                tickfont=dict(color='#4B90B0'),
                tickformat="$,.0f",
                gridcolor='rgba(211,211,211,0.3)',
                anchor="x",
                overlaying="y",
                side="right"
            )
        })
    
    fig.update_layout(layout)
    return fig

def create_sales_summary_with_comparison(data, dimension, date_range):
    """Create a summary DataFrame with both current and previous period metrics."""
    # Convert date_range to datetime if they're date objects
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    # Check if this is a weekly comparison (dates are 7 days apart)
    is_weekly = (end_date - start_date).days == 6
    
    if is_weekly:
        # For weekly comparisons, simply subtract 7 days from both dates
        previous_start = start_date - pd.Timedelta(days=7)
        previous_end = end_date - pd.Timedelta(days=7)
    else:
        # For other periods, use the period length method
        current_period_length = (end_date - start_date).days
        previous_start = start_date - pd.Timedelta(days=current_period_length)
        previous_end = start_date - pd.Timedelta(days=1)
    
    # Ensure data is properly filtered
    current_period_data = data[
        (data['Date'].dt.date >= start_date.date()) &
        (data['Date'].dt.date <= end_date.date())
    ].copy()
    
    previous_period_data = data[
        (data['Date'].dt.date >= previous_start.date()) &
        (data['Date'].dt.date <= previous_end.date())
    ].copy()
    
    # Create summaries for both periods with explicit type handling
    def create_summary(period_data, dimension):
        summary = period_data.groupby(dimension).agg({
            'Sales Dollars': lambda x: x.astype(float).sum(),
            'Units Sold': lambda x: x.astype(int).sum()
        }).reset_index()
        
        summary['Average Price'] = (summary['Sales Dollars'] / 
                                  summary['Units Sold'].replace(0, np.nan)).round(2)
        
        # Calculate percentages of total
        total_sales = summary['Sales Dollars'].sum()
        summary['Revenue %'] = (summary['Sales Dollars'] / total_sales * 100).round(1)
        
        total_units = summary['Units Sold'].sum()
        summary['Units %'] = (summary['Units Sold'] / total_units * 100).round(1)
        
        return summary
    
    current_summary = create_summary(current_period_data, dimension)
    previous_summary = create_summary(previous_period_data, dimension)
    
    # Merge with previous period data
    summary = current_summary.merge(
        previous_summary,
        on=dimension,
        how='left',
        suffixes=('', '_prev')
    )
    
    # Calculate period-over-period changes
    summary['Revenue Change %'] = (
        (summary['Sales Dollars'] - summary['Sales Dollars_prev']) /
        summary['Sales Dollars_prev'].replace(0, np.nan) * 100
    ).round(1)
    
    summary['Units Change %'] = (
        (summary['Units Sold'] - summary['Units Sold_prev']) /
        summary['Units Sold_prev'].replace(0, np.nan) * 100
    ).round(1)
    
    # Handle new items and infinite values
    summary = summary.replace([np.inf, -np.inf], np.nan)
    summary['Revenue Change %'] = summary['Revenue Change %'].fillna('New')
    summary['Units Change %'] = summary['Units Change %'].fillna('New')
    
    # Sort by current period revenue
    summary = summary.sort_values('Sales Dollars', ascending=False)
    
    return summary

def display_sales_summary(summary, dimension_name):
    """Display the sales summary with period comparisons using Streamlit."""
    st.subheader(f"Sales by {dimension_name}")
    
    # Format the DataFrame for display
    display_cols = {
        dimension_name: summary[dimension_name],
        'Current Revenue': summary['Sales Dollars'],
        'vs Prev Period': summary['Revenue Change %'],
        'Current Units': summary['Units Sold'],
        'vs Prev Period ': summary['Units Change %'],  # Extra space to make unique
        'Revenue %': summary['Revenue %']
    }
    
    display_df = pd.DataFrame(display_cols)
    
    # Create the styled DataFrame
    styled_df = display_df.style.format({
        'Current Revenue': '${:,.2f}',
        'Current Units': '{:,}',
        'vs Prev Period': lambda x: f"{x}%" if isinstance(x, (int, float)) else x,
        'vs Prev Period ': lambda x: f"{x}%" if isinstance(x, (int, float)) else x,
        'Revenue %': '{:.1f}%'
    }).apply(lambda x: [
        'color: red' if isinstance(v, (int, float)) and v < 0 else
        'color: green' if isinstance(v, (int, float)) and v > 0 else
        'color: blue' if v == 'New' else
        '' for v in x
    ], subset=['vs Prev Period', 'vs Prev Period '])
    
    st.dataframe(styled_df, use_container_width=True)

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
    
    # Initialize session state for sidebar collapse
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    # Main content
    st.title("Sales Analytics Dashboard")
    
    # Initialize session state
    if 'sheet_id' not in st.session_state:
        config = load_saved_config()
        st.session_state.sheet_id = config.get('sheet_id', '')
        st.session_state.sheet_range = config.get('sheet_range', 'sales_template')

    # Only show detailed sidebar content if not collapsed
    if not st.session_state.sidebar_collapsed:
        with st.sidebar:
            
            # Add template download instructions
            st.markdown(f"""
            ### 🚀 Getting Started
            1. [Download the template spreadsheet]({TEMPLATE_LINK})
            2. Make a copy for your own use (File > Make a copy)
            3. Populate with your sales data following the template format
            4. Grant viewer access to your Google Sheet to analytics-dash@analytics-dash-443921.iam.gserviceaccount.com
            5. Enter your sheet ID (the long string between /d/ and /edit in the URL)
            """)
            
            st.markdown("---")
            st.markdown("### 🔗 Connect Your Data")
            sheet_id = st.text_input(
                "Google Sheet ID", 
                value=st.session_state.sheet_id,
                placeholder="Enter your Sheet ID or leave blank for demo data"
            )
            sheet_range = st.text_input(
                "Sheet Range", 
                value=st.session_state.sheet_range,
                help="Enter sheet name or include range (e.g. 'sales_template' or 'sales_template!A1:H')"
            )
            
            # Save/Clear configuration buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Reset Config"):
                    if os.path.exists(get_config_path()):
                        os.remove(get_config_path())
                    st.session_state.sheet_id = ''
                    st.session_state.sheet_range = 'sales_template'
                    st.success("Cleared!")
                    st.rerun()
            
            with col2:
                if st.button("Load Data"):
                    save_config(sheet_id, sheet_range)
                    st.session_state.sheet_id = sheet_id
                    st.session_state.sheet_range = sheet_range
                    st.success("Saved!")
                
    else:
        # When sidebar is collapsed, we still need the sheet_id value
        sheet_id = st.session_state.sheet_id
        sheet_range = st.session_state.sheet_range

    # Load data based on whether user provided their own sheet ID or using demo data
    if not sheet_id:
        data, error = load_data_from_gsheet(DEMO_SHEET_ID, DEMO_SHEET_RANGE)
        context_data, context_error = load_context_data(DEMO_SHEET_ID)
        if not st.session_state.sidebar_collapsed:
            st.sidebar.info("👆 Currently using demo data. Enter your Sheet ID above to use your own data.")
    else:
        data, error = load_data_from_gsheet(sheet_id, sheet_range)
        context_data, context_error = load_context_data(sheet_id)
    
    if error:
        st.error(error)
        return
    if data is None:
        return

    # Display context section
    try:
        if context_data is not None:
            display_context_section(context_data)
        elif context_error:
            st.info("Context data not available. Please ensure you have a 'data_context' sheet with columns: Category, Description, Notes")
    except Exception as e:
        st.warning(f"Error displaying context section: {str(e)}")

    # Display filters
    retailer_filter, product_filter, date_range = display_filters(data)
    
    # Apply retailer and product filters, but NOT date filter yet
    filtered_data = filter_data(data, retailer_filter, product_filter)
    
    # Create fully filtered data for components that need it
    fully_filtered_data = filter_data(filtered_data, retailer_filter, product_filter, date_range)
    
    # Display sales overview with fully filtered data
    st.plotly_chart(plot_sales_overview(data, fully_filtered_data, retailer_filter, product_filter), use_container_width=True)
    
    # Display sales summaries with comparisons using filtered_data (not fully_filtered_data)
    col1, col2 = st.columns(2)
    
    with col1:
        retailer_summary = create_sales_summary_with_comparison(filtered_data, 'Retailer', date_range)
        display_sales_summary(retailer_summary, 'Retailer')
    
    with col2:
        product_summary = create_sales_summary_with_comparison(filtered_data, 'Product Title', date_range)
        display_sales_summary(product_summary, 'Product Title')
    
    # Combined Size and Color Analysis
    st.subheader("Color and Size Analysis")
    
    # Single product filter for both analyses
    product_filter = st.selectbox(
        "Select Product",
        options=["All"] + sorted(filtered_data['Product Title'].unique().tolist()),
        key="dimension_filter"
    )
    
    # Create tabs for Size and Color analysis
    dimension_tabs = st.tabs(["Size Analysis", "Color Analysis"])
    
    with dimension_tabs[0]:  # Size Analysis
        size_line_fig, size_pie_fig = create_distribution_charts(fully_filtered_data, 'Size', product_filter)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(size_line_fig, use_container_width=True)
        with col2:
            st.plotly_chart(size_pie_fig, use_container_width=True)
    
    with dimension_tabs[1]:  # Color Analysis
        color_line_fig, color_pie_fig = create_distribution_charts(fully_filtered_data, 'Color', product_filter)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(color_line_fig, use_container_width=True)
        with col2:
            st.plotly_chart(color_pie_fig, use_container_width=True)

    # Add enhanced pivot analysis section with comparisons
    create_pivot_analysis_with_comparison(filtered_data, date_range)

if __name__ == "__main__":
    main()
