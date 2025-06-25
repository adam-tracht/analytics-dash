# display_components.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from date_filters import create_date_filter, filter_data_by_dates

def display_context_section(context_data):
    """Display the context information in an expandable section."""
    with st.expander("📝 Data Context & Notes", expanded=False):
        if context_data is None:
            st.info("No context information available.")
            return
            
        for _, row in context_data.iterrows():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"**{row['Category']}**")
            with col2:
                st.markdown(row['Description'])
                if pd.notna(row['Notes']):
                    st.caption(row['Notes'])

def display_filters(data, monthly_data=None):
    """Display consolidated filters in a single row."""
    if monthly_data is not None:
        toggle_col1, toggle_col2 = st.columns([2, 4])
        with toggle_col1:
            st.write("Data View:")
            view_type = st.radio(
                "Select View",
                options=['Weekly', 'Monthly'],
                horizontal=True,
                label_visibility="collapsed"
            )
        current_data = monthly_data if view_type == 'Monthly' else data
    else:
        view_type = 'Weekly'
        current_data = data

        # Use the new date filter component
    start_date, end_date = create_date_filter(
        current_data, 
        view_type=view_type,
        key_prefix='main'
    )
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        retailer_filter = st.multiselect(
            "🏪 Retailers",
            options=["All"] + sorted(current_data['Retailer'].unique().tolist()),
            default="All"
        )
    
    with col2:
        product_filter = st.multiselect(
            "📦 Products",
            options=["All"] + sorted(current_data['Product Title'].unique().tolist()),
            default="All"
        )
    
    return retailer_filter, product_filter, (start_date, end_date), view_type

def plot_sales_overview(data, filtered_data, retailer_filter, product_filter):
    """Create a compact sales overview chart showing both filtered and total data."""
    fig = go.Figure()
    
    # Ensure we're working with proper dataframes
    if data is None or data.empty:
        return go.Figure().update_layout(
            title="No data available",
            height=300
        )
        
    if filtered_data is None or filtered_data.empty:
        return go.Figure().update_layout(
            title="No data available for selected filters",
            height=300
        )
    
    # Group by date
    total_sales = data.groupby('Date')['Sales Dollars'].sum().reset_index()
    filtered_sales = filtered_data.groupby('Date')['Sales Dollars'].sum().reset_index()
    
    # Check if filters are applied
    filters_applied = (isinstance(retailer_filter, list) and "All" not in retailer_filter) or \
                     (isinstance(product_filter, list) and "All" not in product_filter)
    
    # Add total sales trace
    fig.add_trace(go.Scatter(
        x=total_sales['Date'],
        y=total_sales['Sales Dollars'],
        mode='lines',
        name='Total Sales',
        line=dict(color='rgba(200,200,200,0.5)', width=1),
        hovertemplate="<b>Total Sales:</b> $%{y:,.2f}<br>",
        yaxis='y'
    ))
    
    # Add filtered sales trace
    fig.add_trace(go.Scatter(
        x=filtered_sales['Date'],
        y=filtered_sales['Sales Dollars'],
        mode='lines',
        name='Filtered Sales',
        line=dict(color='#4B90B0', width=2),
        hovertemplate="<b>Filtered Sales:</b> $%{y:,.2f}<br>",
        yaxis='y2' if filters_applied else 'y'
    ))
    
    # Base layout - always apply this
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
    
    # If filters are applied, add secondary y-axis
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