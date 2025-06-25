# dashboard.py

import streamlit as st
from pathlib import Path
import json
import os
from datetime import datetime, timedelta, date
from data_loader import (
    load_data_from_gsheet, 
    load_context_data, 
    load_returns_data,
    load_monthly_data
)
from web_metrics_loader import load_web_metrics
from inventory_loader import load_inventory_data
from display_components import (
    display_context_section,
    display_filters,
    plot_sales_overview
)
from sales_analysis import (
    create_sales_summary_with_comparison,
    display_sales_summary,
    create_pivot_analysis_with_comparison
)
from summary_generator import display_performance_summary
from sales_visualizations import (
    create_distribution_charts,
    display_metrics
)
from returns_visualizations import create_returns_analysis
from inventory_visualizations import (
    display_inventory_metrics,
    create_inventory_by_category,
    create_inventory_treemap,
    display_inventory_filters,
    create_historical_inventory_chart,
    clean_inventory_data
)
from web_metrics_visualizations import (
    display_web_metrics_dashboard
)

# Constants - Demo spreadsheet details
DEMO_SHEET_ID = "1Ar7YABu7FIUAAAcq-8YZ6LRDVLh8DVV_cKN0WCU12kY"
DEMO_SHEET_RANGE = "sales_template"
TEMPLATE_LINK = "https://docs.google.com/spreadsheets/d/1Ar7YABu7FIUAAAcq-8YZ6LRDVLh8DVV_cKN0WCU12kY/edit#gid=0"

def get_user_config_path():
    """Get the path to the user-specific configuration file."""
    # Store config in app directory instead of home directory for compatibility with cloud deployments
    config_dir = Path(__file__).parent / '.streamlit_sales_dashboard'
    config_dir.mkdir(exist_ok=True)
    return config_dir / 'user_config.json'

def load_user_config():
    """Load user-specific configuration from file."""
    config_path = get_user_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error loading user configuration: {e}")
    return {}

def save_user_config(sheet_id, sheet_range):
    """Save user-specific configuration to file."""
    config_path = get_user_config_path()
    try:
        config = {
            'sheet_id': sheet_id,
            'sheet_range': sheet_range
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        st.warning(f"Error saving user configuration: {e}")

def render_sidebar():
    """Render the sidebar content."""
    with st.sidebar:
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

        # Load user's saved configuration
        user_config = load_user_config()
        
        # Use session state for sheet ID with proper initialization
        if 'sheet_id' not in st.session_state:
            st.session_state.sheet_id = user_config.get('sheet_id', '')
        if 'sheet_range' not in st.session_state:
            st.session_state.sheet_range = user_config.get('sheet_range', 'sales_template')
            
        sheet_id = st.text_input(
            "Google Sheet ID", 
            value=st.session_state.sheet_id,
            placeholder="Enter your Sheet ID or leave blank for demo data"
        )
        
        sheet_range = 'sales_template'
        
        # Save/Clear configuration buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Reset Config"):
                if os.path.exists(get_user_config_path()):
                    os.remove(get_user_config_path())
                st.session_state.sheet_id = ''
                st.session_state.sheet_range = 'sales_template'
                st.success("Configuration cleared!")
                st.rerun()
        
        with col2:
            if st.button("Load Data"):
                if sheet_id and sheet_id != DEMO_SHEET_ID:  # Only save if it's not the demo sheet
                    save_user_config(sheet_id, sheet_range)
                st.session_state.sheet_id = sheet_id
                st.session_state.sheet_range = sheet_range
                st.success("Configuration saved!")
                st.rerun()
                
        return sheet_id, sheet_range

def filter_data(data, retailer_filter, product_filter, date_range=None):
    """Filter data based on user selections with proper error handling."""
    if data is None or data.empty:
        return data
        
    # Create a copy to avoid modifying original data
    filtered_data = data.copy()
    
    # Type safety - ensure filters are lists
    if not isinstance(retailer_filter, list):
        retailer_filter = ["All"]
    if not isinstance(product_filter, list):
        product_filter = ["All"]
    
    # Apply retailer filter if "All" is not selected
    if "All" not in retailer_filter:
        filtered_data = filtered_data[filtered_data['Retailer'].isin(retailer_filter)]
    
    # Apply product filter if "All" is not selected
    if "All" not in product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(product_filter)]
    
    # Apply date range filter if provided
    if date_range is not None and len(date_range) == 2 and date_range[0] is not None and date_range[1] is not None:
        try:
            filtered_data = filtered_data[
                (filtered_data['Date'].dt.date >= date_range[0]) &
                (filtered_data['Date'].dt.date <= date_range[1])
            ]
        except Exception as e:
            st.error(f"Error applying date filter: {str(e)}")
    
    return filtered_data

def calculate_metrics(filtered_data):
    """Calculate key business metrics from the filtered data."""
    if filtered_data is None or filtered_data.empty:
        return {
            'total_sales': 0,
            'total_units': 0,
            'avg_order_value': 0,
            'unique_products': 0,
            'unique_retailers': 0
        }
        
    try:
        metrics = {
            'total_sales': filtered_data['Sales Dollars'].sum(),
            'total_units': int(filtered_data['Units Sold'].sum()),
            'avg_order_value': (filtered_data['Sales Dollars'].sum() / len(filtered_data)) if len(filtered_data) > 0 else 0,
            'unique_products': filtered_data['Product Title'].nunique(),
            'unique_retailers': filtered_data['Retailer'].nunique()
        }
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        metrics = {
            'total_sales': 0,
            'total_units': 0,
            'avg_order_value': 0,
            'unique_products': 0,
            'unique_retailers': 0
        }
    return metrics

def main():
    st.set_page_config(page_title="Sales Analytics Dashboard", layout="wide")
    
    # Add tabs for Sales, Returns, Inventory, and Web Metrics analysis
    tabs = st.tabs(["📈 Sales Analysis", "↩️ Returns Analysis", "📦 Inventory Analysis", "🌐 Web Metrics"])
    
    # Initialize session state
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False

    # Handle sidebar and configuration
    try:
        if not st.session_state.sidebar_collapsed:
            sheet_id, sheet_range = render_sidebar()
        else:
            sheet_id = st.session_state.get('sheet_id', '')
            sheet_range = st.session_state.get('sheet_range', 'sales_template')
    except Exception as e:
        st.error(f"Error loading sidebar: {str(e)}")
        sheet_id = ''
        sheet_range = 'sales_template'

    # Always use demo data if no sheet ID is provided
    active_sheet_id = sheet_id if sheet_id else DEMO_SHEET_ID
    active_sheet_range = sheet_range if sheet_id else DEMO_SHEET_RANGE

    # Load all data with proper error handling
    try:
        data, error = load_data_from_gsheet(active_sheet_id, active_sheet_range)
        monthly_data, monthly_error = load_monthly_data(active_sheet_id)
        context_data, context_error = load_context_data(active_sheet_id)
        returns_data, returns_error = load_returns_data(active_sheet_id)
        inventory_data, inventory_error = load_inventory_data(active_sheet_id)
        web_metrics_data, web_metrics_error = load_web_metrics(active_sheet_id)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return

    # Show demo data message if using demo sheet
    if not sheet_id and not st.session_state.sidebar_collapsed:
        st.sidebar.info("👆 Currently using demo data. Enter your Sheet ID above to use your own data.")

    if error:
        st.error(error)
        return
    if data is None:
        st.error("No data available")
        return

    with tabs[0]:  # Sales Analysis Tab
        try:
            # Display context information
            if context_data is not None:
                display_context_section(context_data)
            elif context_error:
                st.info("Context data not available. Please ensure you have a 'data_context' sheet.")
    
            # Display filters and get user selections
            retailer_filter, product_filter, date_range, view_type = display_filters(
                data, 
                monthly_data if monthly_data is not None else None
            )
            
            # Use appropriate dataset based on view type
            current_data = monthly_data if view_type == 'Monthly' and monthly_data is not None else data
            
            # Apply filters with safety checks
            if current_data is None or current_data.empty:
                st.warning("No data available for the selected view type")
                return
                
            # Apply filters
            filtered_data = filter_data(current_data, retailer_filter, product_filter)
            fully_filtered_data = filter_data(filtered_data, retailer_filter, product_filter, date_range)
            
            # Display metrics and performance summary
            metrics = calculate_metrics(fully_filtered_data)
            display_metrics(metrics)
    
            # Display performance summary with safety check
            if filtered_data is not None and not filtered_data.empty:
                display_performance_summary(filtered_data, date_range, view_type)
            
            # Display sales overview chart with safety check
            try:
                overview_chart = plot_sales_overview(current_data, fully_filtered_data, retailer_filter, product_filter)
                if overview_chart:
                    st.plotly_chart(overview_chart, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating sales overview: {str(e)}")
            
            # Display sales summaries if data is available
            if not fully_filtered_data.empty:
                col1, col2 = st.columns(2)
                
                try:
                    with col1:
                        retailer_summary = create_sales_summary_with_comparison(
                            filtered_data, 'Retailer', date_range, view_type
                        )
                        display_sales_summary(retailer_summary, 'Retailer')
                except Exception as e:
                    with col1:
                        st.error(f"Error generating retailer summary: {str(e)}")
    
                try:
                    with col2:
                        product_summary = create_sales_summary_with_comparison(
                            filtered_data, 'Product Title', date_range, view_type
                        )
                        display_sales_summary(product_summary, 'Product Title')
                except Exception as e:
                    with col2:
                        st.error(f"Error generating product summary: {str(e)}")
    
                # Create pivot analysis if data is available
                try:
                    create_pivot_analysis_with_comparison(filtered_data, date_range, view_type)
                except Exception as e:
                    st.error(f"Error generating pivot analysis: {str(e)}")
            else:
                st.warning("No data available for the selected filters")
        except Exception as e:
            st.error(f"Error in Sales Analysis tab: {str(e)}")

    with tabs[1]:  # Returns Analysis Tab
        try:
            if returns_error:
                st.error(f"Error loading returns data: {returns_error}")
            elif returns_data is None:
                st.warning("No returns data available. Please ensure you have a 'returns' sheet.")
            else:
                create_returns_analysis(returns_data, date_range)
        except Exception as e:
            st.error(f"Error in Returns Analysis tab: {str(e)}")
            
    with tabs[2]:  # Inventory Analysis Tab
        try:
            if inventory_error:
                st.error(f"Error loading inventory data: {inventory_error}")
            elif inventory_data is None:
                st.warning("No inventory data available. Please ensure you have an 'inventory_data' sheet.")
            else:
                # Clean the inventory data first
                clean_inventory = clean_inventory_data(inventory_data)
                
                # Display inventory filters
                st.subheader("🔍 Filter Inventory Data")
                filtered_inventory, filters = display_inventory_filters(clean_inventory)
                
                # Display metrics for filtered data using sales data for WOS calculations
                st.subheader("📊 Inventory Overview")
                display_inventory_metrics(filtered_inventory, data, filters)
                
                # Historical inventory analysis
                st.subheader("📈 Historical Inventory Analysis")
                historical_fig = create_historical_inventory_chart(filtered_inventory, filters)
                st.plotly_chart(historical_fig, use_container_width=True)
                
                # Display inventory visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    # Category distribution chart
                    fig_category = create_inventory_by_category(filtered_inventory)
                    st.plotly_chart(fig_category, use_container_width=True)
                
                with col2:
                    # Treemap visualization
                    fig_treemap = create_inventory_treemap(filtered_inventory)
                    st.plotly_chart(fig_treemap, use_container_width=True)
        except Exception as e:
            st.error(f"Error in Inventory Analysis tab: {str(e)}")

    with tabs[3]:  # Web Metrics Tab
        try:
            if web_metrics_error:
                st.error(f"Error loading web metrics data: {web_metrics_error}")
            elif web_metrics_data is None:
                st.warning("No web metrics data available. Please ensure you have a 'web_metrics' sheet.")
            else:
                display_web_metrics_dashboard(web_metrics_data, context_data)
        except Exception as e:
            st.error(f"Error in Web Metrics tab: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")