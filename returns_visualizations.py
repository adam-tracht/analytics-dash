# returns_visualizations.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from sales_visualizations import clean_dimension_values
from date_filters import create_date_filter, filter_data_by_dates

def create_returns_analysis(returns_data, date_range=None):
    """Create returns analysis section with visualizations and metrics."""
    if returns_data is None or returns_data.empty:
        st.warning("No returns data available")
        return

    # Global product filter at the top
    product_titles = returns_data['Product Title'].fillna('N/A').unique()
    product_titles = sorted([str(title) for title in product_titles if title is not None])
    global_product_filter = st.multiselect(
        "🎯 Filter All Returns Analysis by Products",
        options=["All"] + product_titles,
        default="All",
        key="global_returns_product_filter"
    )

    # Apply global product filter
    filtered_data = returns_data.copy()
    if "All" not in global_product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(global_product_filter)]

    # Use the consistent date filter component
    start_date, end_date = create_date_filter(
        filtered_data.rename(columns={'Week': 'Date'}),
        view_type='Weekly',
        key_prefix='returns'
    )
    
    # Filter data using the selected date range
    fully_filtered_data = filtered_data[
        (filtered_data['Week'].dt.date >= start_date) &
        (filtered_data['Week'].dt.date <= end_date)
    ]

    if fully_filtered_data.empty:
        st.warning("No data available for the selected filters")
        return
    
    # Overall metrics
    st.subheader("Returns Overview")
    display_returns_metrics(fully_filtered_data)
    
    # Create returns trend chart
    st.subheader("Returns Trend Analysis")
    display_returns_trend(returns_data, filtered_data, fully_filtered_data)
    
    # Create pivot table analysis
    st.subheader("Detailed Returns Analysis")
    create_returns_pivot(fully_filtered_data)

def display_returns_metrics(returns_data):
    """Display overview metrics for returns analysis."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_returns = returns_data['Returns ($)'].sum()
        st.metric("Total Returns", f"${total_returns:,.0f}")
    
    with col2:
        total_units_returned = returns_data['Quantity returned'].sum()
        st.metric("Units Returned", f"{total_units_returned:,.0f}")
    
    with col3:
        avg_return_rate = (returns_data['Quantity returned'].sum() / 
                         returns_data['Quantity ordered'].sum() * 100)
        st.metric("Return Rate (Units)", f"{avg_return_rate:.1f}%")
    
    with col4:
        avg_return_value_rate = (returns_data['Returns ($)'].sum() / 
                               returns_data['Total sales'].sum() * 100)
        st.metric("Return Rate (Revenue)", f"{avg_return_value_rate:.1f}%")

def display_returns_trend(total_data, filtered_data, fully_filtered_data):
    """Display the returns trend analysis chart showing both total and filtered data."""
    metric_type = st.radio(
        "Select Metric",
        ["Revenue", "Units"],
        horizontal=True,
        key="returns_trend_metric"
    )
    
    # Calculate weekly metrics for each dataset
    def calculate_weekly_metrics(data):
        return data.groupby('Week').agg({
            'Returns ($)': 'sum',
            'Total sales': 'sum',
            'Quantity returned': 'sum',
            'Quantity ordered': 'sum'
        }).reset_index()
    
    total_weekly = calculate_weekly_metrics(total_data)
    filtered_weekly = calculate_weekly_metrics(filtered_data)
    fully_filtered_weekly = calculate_weekly_metrics(fully_filtered_data)
    
    # Calculate rates for each dataset
    for df in [total_weekly, filtered_weekly, fully_filtered_weekly]:
        df['Return Rate (Revenue)'] = (df['Returns ($)'] / df['Total sales'] * 100)
        df['Return Rate (Units)'] = (df['Quantity returned'] / df['Quantity ordered'] * 100)
    
    # Create figure
    fig = go.Figure()
    
    # Determine which metrics to use based on selection
    y_field = 'Return Rate (Revenue)' if metric_type == "Revenue" else 'Return Rate (Units)'
    y_title = f"Return Rate ({metric_type} %)"
    
    # Add total data trace (dimmed)
    fig.add_trace(go.Scatter(
        x=total_weekly['Week'],
        y=total_weekly[y_field],
        name="Total Returns",
        line=dict(color='rgba(200,200,200,0.5)', width=1),
        hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                     f"<b>Total Return Rate:</b> %{{y:.1f}}%<extra></extra>"
    ))

    # Add product-filtered trace if different from total
    if len(filtered_weekly) != len(total_weekly):
        fig.add_trace(go.Scatter(
            x=filtered_weekly['Week'],
            y=filtered_weekly[y_field],
            name="Product Filtered",
            line=dict(color='rgba(75,144,176,0.5)', width=1),
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         f"<b>Filtered Return Rate:</b> %{{y:.1f}}%<extra></extra>"
        ))

    # Add date-filtered trace
    fig.add_trace(go.Scatter(
        x=fully_filtered_weekly['Week'],
        y=fully_filtered_weekly[y_field],
        name="Date Range",
        line=dict(color='#FF6B6B', width=2),
        hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                     f"<b>Selected Return Rate:</b> %{{y:.1f}}%<extra></extra>"
    ))
    
    fig.update_layout(
        title='Returns Rate Trend Analysis',
        xaxis=dict(title='Week', showgrid=True, gridcolor='rgba(211,211,211,0.3)'),
        yaxis=dict(
            title=y_title,
            tickformat='.1f',
            ticksuffix='%',
            showgrid=True,
            gridcolor='rgba(211,211,211,0.3)'
        ),
        hovermode='x unified',
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_returns_pivot(returns_data):
    """Create and display the returns pivot table analysis."""
    # Filter controls for pivot table
    filter_col1, filter_col2 = st.columns([1, 1])
    
    with filter_col1:
        dimensions = ['Color', 'Size']
        selected_dimensions = st.multiselect(
            "Select Additional Dimensions",
            options=['Product Title'] + dimensions,
            default=['Product Title'],
            key="returns_pivot_dimensions"
        )

    with filter_col2:
        sort_by = st.selectbox(
            "Sort By",
            ["Returns ($)", "Quantity returned", "Return Rate (Units)", "Return Rate (Revenue)"],
            key="returns_sort_metric"
        )

    # Clean dimension values
    filtered_returns = returns_data.copy()
    for dimension in ['Color', 'Size']:
        filtered_returns = clean_dimension_values(filtered_returns, dimension)
    
    if selected_dimensions:
        try:
            # Create pivot table
            pivot = pd.pivot_table(
                filtered_returns,
                values=['Returns ($)', 'Quantity returned', 'Total sales', 
                       'Quantity ordered'],
                index=selected_dimensions,
                aggfunc='sum',
                margins=True,
                margins_name='Total'
            ).reset_index()
            
            # Calculate return rates
            pivot['Return Rate (Units)'] = (pivot['Quantity returned'] / 
                                          pivot['Quantity ordered'] * 100).round(1)
            pivot['Return Rate (Revenue)'] = (pivot['Returns ($)'] / 
                                            pivot['Total sales'] * 100).round(1)
            
            display_returns_pivot_table(pivot, selected_dimensions, sort_by)
            
        except Exception as e:
            st.error(f"Error creating pivot table: {str(e)}")
    else:
        st.info("Please select at least one dimension for analysis")

def display_returns_pivot_table(pivot, selected_dimensions, sort_by):
    """Format and display the returns pivot table."""
    # Sort by selected metric
    sort_col = sort_by if sort_by in pivot.columns else 'Return Rate (Units)'
    non_total = pivot[pivot[selected_dimensions[0]] != 'Total'].sort_values(
        sort_col, ascending=True)
    total_row = pivot[pivot[selected_dimensions[0]] == 'Total']
    pivot = pd.concat([non_total, total_row])
    
    # Select display columns
    display_cols = {
        **{dim: pivot[dim] for dim in selected_dimensions},
        'Returns ($)': pivot['Returns ($)'],
        'Units Returned': pivot['Quantity returned'],
        'Return Rate (Units)': pivot['Return Rate (Units)'],
        'Return Rate (Revenue)': pivot['Return Rate (Revenue)']
    }
    
    display_df = pd.DataFrame(display_cols)
    
    # Create styler with formatting
    styled_df = display_df.style.format({
        'Returns ($)': '${:,.0f}',
        'Units Returned': '{:,.0f}',
        'Return Rate (Units)': '{:.1f}%',
        'Return Rate (Revenue)': '{:.1f}%'
    })
    
    # Apply conditional formatting to return rates
    styled_df = styled_df.apply(lambda x: [
        'background-color: #b71c1c' if isinstance(v, (int, float)) and v >= 15 else
        'background-color: #d32f2f' if isinstance(v, (int, float)) and v >= 10 else
        'background-color: #ef5350' if isinstance(v, (int, float)) and v >= 5 else
        '' for v in x
    ], subset=['Return Rate (Units)', 'Return Rate (Revenue)'])
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Add download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="Download Analysis",
        data=csv,
        file_name=f"returns_analysis_{'-'.join(selected_dimensions)}.csv",
        mime="text/csv"
    )