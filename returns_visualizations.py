# returns_visualizations.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sales_visualizations import clean_dimension_values

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
    if "All" not in global_product_filter:
        returns_data = returns_data[returns_data['Product Title'].isin(global_product_filter)]

    # Date filter
    st.subheader("Select Date Range")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=returns_data['Week'].min().date() if date_range is None else date_range[0],
            min_value=returns_data['Week'].min().date(),
            max_value=returns_data['Week'].max().date()
        )
    
    with col2:
        # For end date, if the date_range extends beyond available data,
        # use the date_range value but limit validation to available data
        display_end_date = date_range[1] if date_range else returns_data['Week'].max().date()
        actual_max_date = max(returns_data['Week'].max().date(), display_end_date)
        
        end_date = st.date_input(
            "End Date",
            value=display_end_date,
            min_value=returns_data['Week'].min().date(),
            max_value=actual_max_date
        )
    
    # Apply date filter
    returns_data = returns_data[
        (returns_data['Week'].dt.date >= start_date) &
        (returns_data['Week'].dt.date <= end_date)
    ]

    if returns_data.empty:
        st.warning("No data available for the selected filters")
        return
    
    # Overall metrics
    st.subheader("Returns Overview")
    display_returns_metrics(returns_data)
    
    # Create returns trend chart
    st.subheader("Returns Trend Analysis")
    display_returns_trend(returns_data)
    
    # Create pivot table analysis
    st.subheader("Detailed Returns Analysis")
    create_returns_pivot(returns_data)

def display_returns_metrics(returns_data):
    """Display overview metrics for returns analysis."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_returns = returns_data['Returns ($)'].sum()
        st.metric("Total Returns", f"${total_returns:,.2f}")
    
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

def display_returns_trend(returns_data):
    """Display the returns trend analysis chart."""
    metric_type = st.radio(
        "Select Metric",
        ["Revenue", "Units"],
        horizontal=True,
        key="returns_trend_metric"
    )
    
    weekly_returns = returns_data.groupby('Week').agg({
        'Returns ($)': 'sum',
        'Total sales': 'sum',
        'Quantity returned': 'sum',
        'Quantity ordered': 'sum'
    }).reset_index()
    
    # Calculate rates
    weekly_returns['Return Rate (Revenue)'] = (weekly_returns['Returns ($)'] / 
                                             weekly_returns['Total sales'] * 100)
    weekly_returns['Return Rate (Units)'] = (weekly_returns['Quantity returned'] / 
                                           weekly_returns['Quantity ordered'] * 100)
    
    fig = go.Figure()
    
    if metric_type == "Revenue":
        fig.add_trace(go.Scatter(
            x=weekly_returns['Week'],
            y=weekly_returns['Return Rate (Revenue)'],
            name='Return Rate (Revenue)',
            mode='lines+markers',
            line=dict(color='#FF6B6B'),
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Return Rate:</b> %{y:.1f}%<extra></extra>"
        ))
        y_title = "Return Rate (Revenue %)"
    else:
        fig.add_trace(go.Scatter(
            x=weekly_returns['Week'],
            y=weekly_returns['Return Rate (Units)'],
            name='Return Rate (Units)',
            mode='lines+markers',
            line=dict(color='#4ECDC4'),
            hovertemplate="<b>Week:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Return Rate:</b> %{y:.1f}%<extra></extra>"
        ))
        y_title = "Return Rate (Units %)"
    
    fig.update_layout(
        xaxis=dict(title='Week'),
        yaxis=dict(
            title=y_title,
            tickformat='.1f',
            ticksuffix='%'
        ),
        hovermode='x unified',
        template='plotly_white',
        height=400
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
            st.write("Debug information:", {
                'data_shape': returns_data.shape,
                'selected_dimensions': selected_dimensions
            })
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
        'Returns ($)': '${:,.2f}',
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