# display_components.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import timedelta

def get_date_range(timeframe, data, view_type='Weekly'):
    """Get start and end dates based on selected timeframe."""
    min_date = data['Date'].min().date()
    max_date = data['Date'].max().date()
    
    if timeframe == 'Custom':
        return None
        
    today = pd.Timestamp.now().date()
    last_complete_month = (today.replace(day=1) - timedelta(days=1))
    
    if timeframe == '1W' and view_type == 'Weekly':
        days_since_sunday = today.weekday() + 1
        last_sunday = today - timedelta(days=days_since_sunday)
        end_date = last_sunday
        start_date = end_date - timedelta(days=6)
        return start_date, end_date
    
    end_date = last_complete_month
    
    if timeframe == '1M':
        if view_type == 'Monthly':
            start_date = end_date.replace(day=1)
        else:
            start_date = end_date - timedelta(days=29)
    elif timeframe == '3M':
        year = end_date.year
        month = end_date.month - 2
        if month <= 0:
            year -= 1
            month = 12 + month
        start_date = pd.Timestamp(year=year, month=month, day=1).date()
    elif timeframe == '6M':
        year = end_date.year
        month = end_date.month - 5
        if month <= 0:
            year -= 1
            month = 12 + month
        start_date = pd.Timestamp(year=year, month=month, day=1).date()
    elif timeframe == '1Y':
        start_date = pd.Timestamp(year=end_date.year - 1, month=end_date.month, day=1).date()
    
    if timeframe != '1W':
        start_date = max(start_date, min_date)
        end_date = min(end_date, max_date)
    
    return start_date, end_date

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
        with toggle_col2:
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

    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
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
    
    with col3:
        timeframe_options = ['1W', '1M', '3M', '6M', '1Y', 'Custom'] if view_type == 'Weekly' else ['1M', '3M', '6M', '1Y', 'Custom']
        timeframe = st.selectbox(
            "📅 Time Range",
            options=timeframe_options,
            index=1 if view_type == 'Monthly' else 0,
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
                value=(current_data['Date'].min().date(), current_data['Date'].max().date()),
                min_value=current_data['Date'].min().date(),
                max_value=current_data['Date'].max().date(),
                label_visibility="collapsed"
            )
        else:
            date_range = get_date_range(timeframe, current_data, view_type)
            if date_range:
                if timeframe == '1W' and date_range[1] > current_data['Date'].max().date():
                    st.write(f"{date_range[0].strftime('%Y-%m-%d')} to")
                    st.write(f"{date_range[1].strftime('%Y-%m-%d')}")
                    st.caption("⚠️ Data through end of week")
                else:
                    st.write(f"{date_range[0].strftime('%Y-%m-%d')} to")
                    st.write(f"{date_range[1].strftime('%Y-%m-%d')}")
    
    return retailer_filter, product_filter, date_range, view_type if monthly_data is not None else 'Weekly'

def plot_sales_overview(data, filtered_data, retailer_filter, product_filter):
    """Create a compact sales overview chart showing both filtered and total data."""
    fig = go.Figure()
    
    total_sales = data.groupby('Date')['Sales Dollars'].sum().reset_index()
    filtered_sales = filtered_data.groupby('Date')['Sales Dollars'].sum().reset_index()
    
    filters_applied = ("All" not in retailer_filter) or ("All" not in product_filter)
    
    fig.add_trace(go.Scatter(
        x=total_sales['Date'],
        y=total_sales['Sales Dollars'],
        mode='lines',
        name='Total Sales',
        line=dict(color='rgba(200,200,200,0.5)', width=1),
        hovertemplate="<b>Total Sales:</b> $%{y:,.2f}<br>",
        yaxis='y'
    ))
    
    fig.add_trace(go.Scatter(
        x=filtered_sales['Date'],
        y=filtered_sales['Sales Dollars'],
        mode='lines',
        name='Filtered Sales',
        line=dict(color='#4B90B0', width=2),
        hovertemplate="<b>Filtered Sales:</b> $%{y:,.2f}<br>",
        yaxis='y2' if filters_applied else 'y'
    ))
    
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