# sales_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
from sales_visualizations import clean_dimension_values, create_distribution_charts

def create_sales_summary_with_comparison(data, dimension, date_range, view_type='Weekly'):
    """Create a summary DataFrame with both current and previous period metrics."""
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    # Handle edge case where start and end dates are the same
    if start_date == end_date:
        # Use the single date as the end date and calculate start date based on view type
        if view_type == 'Monthly':
            # For monthly view, use previous month
            previous_end = start_date - pd.DateOffset(months=1)
            previous_start = previous_end
        else:
            # For weekly/daily view, use previous day
            previous_end = start_date - pd.Timedelta(days=1)
            previous_start = previous_end
    else:
        if view_type == 'Monthly':
            # Calculate the period length in months
            months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
            
            # For monthly view(s), shift back by the appropriate number of months
            previous_start = start_date - pd.DateOffset(months=months_diff)
            previous_end = end_date - pd.DateOffset(months=months_diff)
        else:
            period_length = (end_date - start_date).days
            previous_start = start_date - pd.Timedelta(days=period_length + 1)
            previous_end = start_date - pd.Timedelta(days=1)
    
    # Get data for current period
    current_period_data = data[
        (data['Date'].dt.date >= start_date.date()) &
        (data['Date'].dt.date <= end_date.date())
    ].copy()
    
    # Get data for previous period
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
    
    # Merge current and previous summaries
    summary = current_summary.merge(
        previous_summary,
        on=dimension,
        how='left',
        suffixes=('', '_prev')
    )
    
    # Calculate changes
    summary['Revenue Change %'] = (
        (summary['Sales Dollars'] - summary['Sales Dollars_prev']) /
        summary['Sales Dollars_prev'].replace(0, np.nan) * 100
    ).round(1)
    
    summary['Units Change %'] = (
        (summary['Units Sold'] - summary['Units Sold_prev']) /
        summary['Units Sold_prev'].replace(0, np.nan) * 100
    ).round(1)
    
    # Handle infinities and NaN values
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
        'Current Revenue': '${:,.0f}',
        'Current Units': '{:,}',
        'Revenue %': '{:.1f}%'
    })
    
    def style_numeric_change(val):
        if isinstance(val, str):
            if val == 'New':
                return 'color: #2563eb'  # Blue
            val = val.replace('%', '')
            try:
                num = float(val)
                if num < 0:
                    return 'color: #dc2626'  # Red
                elif num > 0:
                    return 'color: #16a34a'  # Green
            except ValueError:
                pass
        return ''
    
    # Apply styling to comparison columns
    styled_df = styled_df.map(style_numeric_change, subset=['vs Prev Period', 'vs Prev Period '])
    
    st.dataframe(styled_df, use_container_width=True)

def create_pivot_analysis_with_comparison(data, date_range, view_type='Weekly'):
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
    
    # Convert date_range to datetime
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    # Handle edge case where start and end dates are the same
    if start_date == end_date:
        if view_type == 'Monthly':
            previous_end = start_date - pd.DateOffset(months=1)
            previous_start = previous_end
        else:
            previous_end = start_date - pd.Timedelta(days=1)
            previous_start = previous_end
    else:
        if view_type == 'Monthly':
            # Calculate number of months in current period
            months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
            previous_start = start_date - pd.DateOffset(months=months_diff)
            previous_end = end_date - pd.DateOffset(months=months_diff)
        else:
            period_length = (end_date - start_date).days
            previous_start = start_date - pd.Timedelta(days=period_length + 1)
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
            
            merged_pivot['% of Total'] = (merged_pivot[metric] / current_total * 100).round(1)
            
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
                'Change %': merged_pivot['Change %'].astype(str),
                '% of Total': merged_pivot['% of Total']
            }
            
            display_df = pd.DataFrame(display_cols)
            
            # Style the dataframe
            number_format = '${:,.0f}' if metric == 'Sales Dollars' else '{:,.0f}'
            styled_df = (display_df.style
                .format({
                    'Current Period': number_format,
                    'Previous Period': number_format,
                    'Change %': lambda x: f"{x}%" if x != 'New' else x,
                    '% of Total': '{:.1f}%'
                })
                .applymap(lambda x: 'color: red' if isinstance(x, str) and x != 'New' and '-' in x else
                         'color: green' if isinstance(x, str) and x != 'New' and x.replace('.', '').isdigit() else
                         'color: blue' if x == 'New' else '',
                         subset=['Change %'])
            )
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Add period information
            st.caption(f"""Current Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
                         Previous Period: {previous_start.strftime('%Y-%m-%d')} to {previous_end.strftime('%Y-%m-%d')}""")
            
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
    else:
        st.info("Please select at least one dimension for analysis")