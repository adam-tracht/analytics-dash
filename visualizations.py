# visualizations.py
from datetime import timedelta
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def clean_dimension_values(data, dimension):
    """Clean dimension values by replacing empty, null, and zero values with 'N/A'"""
    if dimension in ['Color', 'Size']:
        # Create a copy to avoid modifying the original
        data = data.copy()
        
        # Convert column to string type first
        data[dimension] = data[dimension].astype(str)
        
        # List of values to replace with 'N/A'
        replace_values = ['0', '0.0', 'nan', 'None', 'none', 'null', '', ' ']
        
        # Replace all empty/null/zero values with 'N/A'
        data[dimension] = data[dimension].replace(replace_values, 'N/A')
        
        # Also replace any whitespace-only strings with 'N/A'
        data[dimension] = data[dimension].apply(lambda x: 'N/A' if x.strip() == '' else x)
        
    return data

def plot_sales_trend(data, moving_averages, show_daily, show_annotations):
    """Create an enhanced interactive sales trend visualization."""
    if data.empty:
        return None
        
    daily_sales = data.groupby('Date')['Sales Dollars'].sum().reset_index()
    
    fig = go.Figure()
    
    # Add daily sales trace
    trace_mode = 'lines+markers' if show_daily else 'lines'
    fig.add_trace(go.Scatter(
        x=daily_sales['Date'],
        y=daily_sales['Sales Dollars'],
        mode=trace_mode,
        name='Daily Sales',
        line=dict(color='#4B90B0', width=1),
        marker=dict(size=4),
        hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Sales:</b> $%{y:,.2f}<br>"
    ))
    
    # Add moving averages
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    for i, period in enumerate(moving_averages):
        ma = daily_sales['Sales Dollars'].rolling(window=period).mean()
        fig.add_trace(go.Scatter(
            x=daily_sales['Date'],
            y=ma,
            mode='lines',
            name=f'{period}-day MA',
            line=dict(color=colors[i % len(colors)], width=2, dash='dash'),
            hovertemplate=f"<b>{period}-day MA:</b> $%{{y:,.2f}}<br>"
        ))
    
    fig.update_layout(
        title='Daily Sales Trend Analysis',
        template='plotly_white',
        hovermode='x unified',
        xaxis=dict(title='Date', showgrid=True, gridcolor='rgba(211,211,211,0.3)'),
        yaxis=dict(title='Revenue ($)', tickformat="$,.0f", gridcolor='rgba(211,211,211,0.3)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=100)
    )
    
    return fig

def create_distribution_charts(data, dimension, selected_product="All"):
    """Create line and pie charts showing sales distribution by dimension (Color/Size)."""
    # Create a copy of the data to avoid modifying the original
    data = data.copy()
    
    # Clean dimension values
    data = clean_dimension_values(data, dimension)
    
    if selected_product != "All":
        data = data[data['Product Title'] == selected_product]
    
    # Prepare data for charts
    dim_sales = data.groupby([dimension, 'Date'])['Sales Dollars'].sum().reset_index()
    dim_totals = data.groupby(dimension)['Sales Dollars'].sum().reset_index()
    
    # Calculate total sales and percentages
    total_sales = dim_totals['Sales Dollars'].sum()
    dim_totals['Percentage'] = (dim_totals['Sales Dollars'] / total_sales * 100).round(2)
    
    # Sort by sales value descending
    dim_totals = dim_totals.sort_values('Sales Dollars', ascending=False)
    
    # Separate main categories and others (those less than 5%)
    main_cats = dim_totals[dim_totals['Percentage'] >= 5].copy()
    other_cats = dim_totals[dim_totals['Percentage'] < 5]
    
    if not other_cats.empty:
        other_row = pd.DataFrame({
            dimension: ['Other'],
            'Sales Dollars': [other_cats['Sales Dollars'].sum()],
            'Percentage': [other_cats['Percentage'].sum()]
        })
        dim_totals = pd.concat([main_cats, other_row]).reset_index(drop=True)
    
    # Create line chart
    line_fig = go.Figure()
    
    # Add trace for each main category
    for cat in main_cats[dimension].unique():
        cat_data = dim_sales[dim_sales[dimension] == cat]
        line_fig.add_trace(go.Scatter(
            x=cat_data['Date'],
            y=cat_data['Sales Dollars'],
            name=str(cat),
            mode='lines',
            hovertemplate=f"<b>{dimension}:</b> {cat}<br>" +
                         "<b>Date:</b> %{x|%Y-%m-%d}<br>" +
                         "<b>Sales:</b> $%{y:,.2f}<extra></extra>"
        ))
    
    line_fig.update_layout(
        title=f'Sales Trend by {dimension} (>5% of total sales)',
        template='plotly_white',
        hovermode='x unified',
        xaxis=dict(
            title='Date',
            showgrid=True,
            gridcolor='rgba(211,211,211,0.3)'
        ),
        yaxis=dict(
            title='Revenue ($)',
            tickformat="$,.0f",
            gridcolor='rgba(211,211,211,0.3)'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=100)
    )
    
    # Create pie chart
    pie_fig = go.Figure(data=[go.Pie(
        labels=dim_totals[dimension],
        values=dim_totals['Sales Dollars'],
        hole=.3,
        hovertemplate=f"<b>{dimension}:</b> %{{label}}<br>" +
                     "<b>Sales:</b> $%{value:,.2f}<br>" +
                     "<b>Percentage:</b> %{percent:.1f}%<extra></extra>"
    )])
    
    pie_fig.update_layout(
        title=f'Sales Distribution by {dimension}',
        template='plotly_white'
    )
    
    return line_fig, pie_fig

def display_metrics(metrics):
    """Display key business metrics in a clean layout."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Revenue", f"${metrics['total_sales']:,.2f}")
    
    with col2:
        st.metric("Total Units", f"{metrics['total_units']:,}")
        
    with col3:
        st.metric("Avg Order Value", f"${metrics['avg_order_value']:,.2f}")
        
    with col4:
        st.metric("Unique Products", str(metrics['unique_products']))
        
    with col5:
        st.metric("Active Retailers", str(metrics['unique_retailers']))

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
    
    # Get current period data - convert timestamps to dates for comparison
    current_data = filtered_data[
        (filtered_data['Date'].dt.date >= start_date.date()) &
        (filtered_data['Date'].dt.date <= end_date.date())
    ].copy()
    
    # Get previous period data - convert timestamps to dates for comparison
    previous_data = filtered_data[
        (filtered_data['Date'].dt.date >= previous_start.date()) &
        (filtered_data['Date'].dt.date <= previous_end.date())
    ].copy()
    
    # Clean dimension values for Color and Size
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
            # Create current period pivot
            current_pivot = pd.pivot_table(
                current_data,
                values=metric,
                index=selected_rows,
                aggfunc='sum',
                margins=True,
                margins_name='Total'
            ).reset_index()
            
            # Create previous period pivot
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
            
            # Sort by current period metric (keeping Total at bottom)
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
            
            def style_change_column(value):
                """Style the change column based on value."""
                if value == 'New':
                    return 'color: blue'
                try:
                    val = float(value)
                    if val < 0:
                        return 'color: red'
                    elif val > 0:
                        return 'color: green'
                    return ''
                except:
                    return ''
            
            # Style the dataframe
            number_format = '${:,.2f}' if metric == 'Sales Dollars' else '{:,.0f}'
            styled_df = (display_df.style
                .format({
                    'Current Period': number_format,
                    'Previous Period': number_format,
                    'Change %': lambda x: f"{x}%" if x != 'New' else x,
                    '% of Total': '{:.1f}%'
                })
                .applymap(style_change_column, subset=['Change %'])
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
            st.write("Debug information:")
            st.write({
                'current_data_shape': current_data.shape if 'current_data' in locals() else None,
                'previous_data_shape': previous_data.shape if 'previous_data' in locals() else None,
                'selected_rows': selected_rows,
                'metric': metric
            })
    else:
        st.info("Please select at least one dimension for analysis")

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
        end_date = st.date_input(
            "End Date",
            value=returns_data['Week'].max().date() if date_range is None else date_range[1],
            min_value=returns_data['Week'].min().date(),
            max_value=returns_data['Week'].max().date()
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
    
    # Create returns trend chart with toggle
    st.subheader("Returns Trend Analysis")
    
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
    
    # Create pivot table analysis
    st.subheader("Detailed Returns Analysis")
    
    # Filter controls for pivot table
    filter_col1, filter_col2 = st.columns([1, 1])
    
    with filter_col1:
        # Available dimensions for pivot table (Product Title already filtered globally)
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
            
            # Format numbers first
            display_df = display_df.copy()
            numeric_display_df = display_df.copy()
            
            # Create styler with basic formatting
            styled_df = display_df.style.format({
                'Returns ($)': '${:,.2f}',
                'Units Returned': '{:,.0f}',
                'Return Rate (Units)': '{:.1f}%',
                'Return Rate (Revenue)': '{:.1f}%'
            })
            
            # Define style function
            def color_return_rates(val):
                """Style return rates based on value."""
                try:
                    if isinstance(val, str):
                        val = float(val.rstrip('%'))
                    
                    if pd.isna(val):
                        return ''
                    elif val >= -5:
                        return ''  # Default background for low return rates
                    elif val >= -10:
                        return 'background-color: #ef5350'  # Medium red
                    elif val >= -15:
                        return 'background-color: #d32f2f'  # Darker red
                    else:
                        return 'background-color: #b71c1c'  # Darkest red
                except:
                    return ''
            
            # Apply styles to return rate columns
            styled_df = styled_df.apply(lambda x: [color_return_rates(v) for v in x], 
                                      subset=['Return Rate (Units)', 'Return Rate (Revenue)'])
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Add download button
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download Analysis",
                data=csv,
                file_name=f"returns_analysis_{'-'.join(selected_dimensions)}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Error creating pivot table: {str(e)}")
            st.write("Debug information:")
            st.write({
                'data_shape': returns_data.shape,
                'selected_dimensions': selected_dimensions
            })
    else:
        st.info("Please select at least one dimension for analysis")
