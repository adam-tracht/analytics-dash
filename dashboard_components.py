# dashboard_components.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import timedelta
from sales_visualizations import (
    clean_dimension_values,
    create_distribution_charts,
    plot_sales_trend
)

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

def create_sales_summary_with_comparison(data, dimension, date_range, view_type='Weekly'):
    """Create a summary DataFrame with both current and previous period metrics."""
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    if view_type == 'Monthly':
        # Calculate the period length in months
        months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        
        # For monthly view(s), shift back by the appropriate number of months
        previous_start = start_date - pd.DateOffset(months=months_diff)
        previous_end = end_date - pd.DateOffset(months=months_diff)
    else:
        is_weekly = (end_date - start_date).days == 6
        if is_weekly:
            previous_start = start_date - pd.Timedelta(days=7)
            previous_end = end_date - pd.Timedelta(days=7)
        else:
            current_period_length = (end_date - start_date).days
            previous_start = start_date - pd.Timedelta(days=current_period_length + 1)
            previous_end = start_date - pd.Timedelta(days=1)
    
    current_period_data = data[
        (data['Date'].dt.date >= start_date.date()) &
        (data['Date'].dt.date <= end_date.date())
    ].copy()
    
    previous_period_data = data[
        (data['Date'].dt.date >= previous_start.date()) &
        (data['Date'].dt.date <= previous_end.date())
    ].copy()
    
    def create_summary(period_data, dimension):
        if period_data.empty:
            return pd.DataFrame(columns=[dimension, 'Sales Dollars', 'Units Sold', 
                                      'Average Price', 'Revenue %', 'Units %'])
            
        summary = period_data.groupby(dimension).agg({
            'Sales Dollars': lambda x: x.astype(float).sum(),
            'Units Sold': lambda x: x.astype(int).sum()
        }).reset_index()
        
        summary['Average Price'] = (summary['Sales Dollars'] / 
                                  summary['Units Sold'].replace(0, np.nan)).round(2)
        
        total_sales = summary['Sales Dollars'].sum()
        summary['Revenue %'] = (summary['Sales Dollars'] / total_sales * 100).round(1)
        
        total_units = summary['Units Sold'].sum()
        summary['Units %'] = (summary['Units Sold'] / total_units * 100).round(1)
        
        return summary
    
    current_summary = create_summary(current_period_data, dimension)
    previous_summary = create_summary(previous_period_data, dimension)
    
    summary = current_summary.merge(
        previous_summary,
        on=dimension,
        how='left',
        suffixes=('', '_prev')
    )
    
    summary['Revenue Change %'] = (
        (summary['Sales Dollars'] - summary['Sales Dollars_prev']) /
        summary['Sales Dollars_prev'].replace(0, np.nan) * 100
    ).round(1)
    
    summary['Units Change %'] = (
        (summary['Units Sold'] - summary['Units Sold_prev']) /
        summary['Units Sold_prev'].replace(0, np.nan) * 100
    ).round(1)
    
    summary = summary.replace([np.inf, -np.inf], np.nan)
    summary['Revenue Change %'] = summary['Revenue Change %'].fillna('New')
    summary['Units Change %'] = summary['Units Change %'].fillna('New')
    
    return summary.sort_values('Sales Dollars', ascending=False)

def display_sales_summary(summary, dimension_name):
    """Display the sales summary with period comparisons."""
    st.subheader(f"Sales by {dimension_name}")
    
    display_cols = {
        dimension_name: summary[dimension_name],
        'Current Revenue': summary['Sales Dollars'],
        'vs Prev Period': summary['Revenue Change %'].astype(str).apply(
            lambda x: f"{float(x)}%" if x.replace('.', '').replace('-', '').isdigit() else x
        ),
        'Current Units': summary['Units Sold'],
        'vs Prev Period ': summary['Units Change %'].astype(str).apply(
            lambda x: f"{float(x)}%" if x.replace('.', '').replace('-', '').isdigit() else x
        ),
        'Revenue %': summary['Revenue %']
    }
    
    display_df = pd.DataFrame(display_cols)
    
    styled_df = display_df.style.format({
        'Current Revenue': '${:,.2f}',
        'Current Units': '{:,}',
        'Revenue %': '{:.1f}%'
    })
    
    def color_changes(val):
        if isinstance(val, str):
            if val == 'New':
                return 'color: blue'
            val = val.replace('%', '')
            try:
                num = float(val)
                if num < 0:
                    return 'color: red'
                elif num > 0:
                    return 'color: green'
            except ValueError:
                pass
        return ''
    
    styled_df = styled_df.applymap(color_changes, subset=['vs Prev Period', 'vs Prev Period '])
    st.dataframe(styled_df, use_container_width=True)

def create_pivot_analysis_with_comparison(data, date_range):
    """Create an interactive pivot table analysis section with period comparisons."""
    st.subheader("Interactive Pivot Table")
    
    # Create filter columns
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        retailer_filter = st.multiselect(
            "Filter by Retailers",
            options=["All"] + sorted(data['Retailer'].unique().tolist()),
            default="All",
            key="pivot_retailer_filter"
        )
    
    with filter_col2:
        product_filter = st.multiselect(
            "Filter by Products",
            options=["All"] + sorted(data['Product Title'].unique().tolist()),
            default="All",
            key="pivot_product_filter"
        )
    
    # Filter data for both periods
    filtered_data = data.copy()
    if "All" not in retailer_filter:
        filtered_data = filtered_data[filtered_data['Retailer'].isin(retailer_filter)]
    if "All" not in product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(product_filter)]
    
    # Convert date_range to datetime if they're date objects
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    # Get the first day of the current month
    current_month_start = start_date.replace(day=1)
    
    # Check if this is a monthly view by checking if start_date is the first of the month
    is_monthly = start_date.day == 1
    
    if is_monthly:
        # Calculate the period length in months
        months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        
        # For monthly view(s), shift back by the appropriate number of months
        previous_start = start_date - pd.DateOffset(months=months_diff)
        previous_end = end_date - pd.DateOffset(months=months_diff)
    else:
        # Check if this is a weekly comparison
        is_weekly = (end_date - start_date).days == 6
        
        if is_weekly:
            # For weekly comparisons, subtract 7 days from both dates
            previous_start = start_date - pd.Timedelta(days=7)
            previous_end = end_date - pd.Timedelta(days=7)
        else:
            # For other periods, use the period length method
            period_length = (end_date - start_date).days
            previous_start = start_date - pd.Timedelta(days=period_length)
            previous_end = start_date - pd.Timedelta(days=1)
    
    # Get data for both periods
    current_data = filtered_data[
        (filtered_data['Date'].dt.date >= start_date.date()) &
        (filtered_data['Date'].dt.date <= end_date.date())
    ].copy()
    
    previous_data = filtered_data[
        (filtered_data['Date'].dt.date >= previous_start.date()) &
        (filtered_data['Date'].dt.date <= previous_end.date())
    ].copy()
    
    # Clean dimension values
    for dimension in ['Color', 'Size']:
        current_data = clean_dimension_values(current_data, dimension)
        previous_data = clean_dimension_values(previous_data, dimension)
    
    # Available dimensions for pivot table
    dimensions = ['Retailer', 'Product Title', 'Color', 'Size']
    
    # Create selection columns
    col1, col2 = st.columns([2, 2])
    with col1:
        selected_rows = st.multiselect(
            "Select Row Dimensions",
            options=dimensions,
            default=['Retailer'],
            help="Select dimensions to analyze"
        )
    
    with col2:
        metric = st.radio(
            "Select Metric",
            options=['Sales Dollars', 'Units Sold'],
            horizontal=True
        )
    
    if selected_rows:
        try:
            # Create pivots and merge
            current_pivot = pd.pivot_table(
                current_data,
                values=metric,
                index=selected_rows,
                aggfunc='sum',
                margins=True,
                margins_name='Total'
            ).reset_index()
            
            previous_pivot = pd.pivot_table(
                previous_data,
                values=metric,
                index=selected_rows,
                aggfunc='sum',
                margins=True,
                margins_name='Total'
            ).reset_index()
            
            # Merge pivots
            merged_pivot = current_pivot.merge(
                previous_pivot,
                on=selected_rows,
                how='outer',
                suffixes=('', '_prev')
            ).fillna(0)
            
            # Calculate metrics
            current_total = merged_pivot[metric].sum()
            merged_pivot['Change %'] = np.where(
                merged_pivot[f"{metric}_prev"] == 0,
                'New',
                ((merged_pivot[metric] - merged_pivot[f"{metric}_prev"]) / 
                 merged_pivot[f"{metric}_prev"] * 100).round(1)
            )
            
            merged_pivot['% of Total'] = (merged_pivot[metric] / (current_total / 2) * 100).round(1)
            
            # Sort and format for display
            non_total = merged_pivot[merged_pivot[selected_rows[0]] != 'Total'].sort_values(
                metric, ascending=False)
            total_row = merged_pivot[merged_pivot[selected_rows[0]] == 'Total']
            merged_pivot = pd.concat([non_total, total_row])
            
            # Format display
            display_cols = {
                **{dim: merged_pivot[dim] for dim in selected_rows},
                'Current Period': merged_pivot[metric],
                'Previous Period': merged_pivot[f"{metric}_prev"],
                'Change %': merged_pivot['Change %'],
                '% of Total': merged_pivot['% of Total']
            }
            
            display_df = pd.DataFrame(display_cols)
            
            # Style the dataframe
            number_format = '${:,.2f}' if metric == 'Sales Dollars' else '{:,.0f}'
            styled_df = (display_df.style
                .format({
                    'Current Period': number_format,
                    'Previous Period': number_format,
                    'Change %': lambda x: f"{x}%" if x != 'New' else x,
                    '% of Total': '{:.1f}%'
                })
                .applymap(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else
                         'color: green' if isinstance(x, (int, float)) and x > 0 else
                         'color: blue' if x == 'New' else '',
                         subset=['Change %'])
            )
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Add download button
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download Analysis",
                data=csv,
                file_name=f"pivot_analysis_{'-'.join(selected_rows)}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Error creating pivot table: {str(e)}")
            st.write("Debug information:", {
                'current_data_shape': current_data.shape if 'current_data' in locals() else None,
                'previous_data_shape': previous_data.shape if 'previous_data' in locals() else None,
                'selected_rows': selected_rows,
                'metric': metric
            })
    else:
        st.info("Please select at least one dimension for analysis")