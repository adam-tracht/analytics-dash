# visualizations.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

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
    if selected_product != "All":
        data = data[data['Product Title'] == selected_product]
    
    # Prepare data for charts
    dim_sales = data.groupby([dimension, 'Date'])['Sales Dollars'].sum().reset_index()
    dim_totals = data.groupby(dimension)['Sales Dollars'].sum().reset_index()
    
    total_sales = dim_totals['Sales Dollars'].sum()
    dim_totals['Percentage'] = dim_totals['Sales Dollars'] / total_sales * 100
    
    # Separate main categories and others
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
    for cat in main_cats[dimension].unique():
        cat_data = dim_sales[dim_sales[dimension] == cat]
        line_fig.add_trace(go.Scatter(
            x=cat_data['Date'],
            y=cat_data['Sales Dollars'],
            name=str(cat),
            mode='lines',
            hovertemplate=f"<b>Date:</b> %{{x|%Y-%m-%d}}<br><b>Sales:</b> $%{{y:,.2f}}<br>"
        ))
    
    line_fig.update_layout(
        title=f'Sales Trend by {dimension} (>5% of total sales)',
        template='plotly_white',
        hovermode='x unified',
        xaxis=dict(title='Date', showgrid=True, gridcolor='rgba(211,211,211,0.3)'),
        yaxis=dict(title='Revenue ($)', tickformat="$,.0f", gridcolor='rgba(211,211,211,0.3)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=100)
    )
    
    # Create pie chart
    pie_fig = go.Figure(data=[go.Pie(
        labels=dim_totals[dimension],
        values=dim_totals['Sales Dollars'],
        hole=.3,
        hovertemplate=f"<b>{dimension}:</b> %{{label}}<br><b>Sales:</b> $%{{value:,.2f}}<br><b>Percentage:</b> %{{percent:.1f}}%<extra></extra>"
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

def display_performance_analysis(filtered_data):
    """Display detailed performance analysis tabs."""
    tabs = st.tabs(["By Retailer", "By Product", "Detailed View"])
    
    with tabs[0]:
        retailer_metrics = filtered_data.groupby('Retailer').agg({
            'Sales Dollars': 'sum',
            'Units Sold': 'sum'
        }).reset_index()
        retailer_metrics['Average Price'] = retailer_metrics['Sales Dollars'] / retailer_metrics['Units Sold']
        retailer_metrics = retailer_metrics.sort_values('Sales Dollars', ascending=False)
        st.dataframe(retailer_metrics.style.format({
            'Sales Dollars': '${:,.2f}',
            'Units Sold': '{:,}',
            'Average Price': '${:.2f}'
        }))
    
    with tabs[1]:
        product_metrics = filtered_data.groupby('Product Title').agg({
            'Sales Dollars': 'sum',
            'Units Sold': 'sum'
        }).reset_index()
        product_metrics['Average Price'] = product_metrics['Sales Dollars'] / product_metrics['Units Sold']
        product_metrics = product_metrics.sort_values('Sales Dollars', ascending=False)
        st.dataframe(product_metrics.style.format({
            'Sales Dollars': '${:,.2f}',
            'Units Sold': '{:,}',
            'Average Price': '${:.2f}'
        }))
    
    with tabs[2]:
        st.dataframe(
            filtered_data.sort_values('Date', ascending=False),
            column_config={
                "Sales Dollars": st.column_config.NumberColumn(
                    "Revenue",
                    format="$%.2f"
                ),
                "Units Sold": st.column_config.NumberColumn(
                    "Units",
                    format="%d"
                )
            }
        )

def display_product_analysis(filtered_data):
    """Display color and size analysis sections."""
    # Color Analysis
    st.subheader("🎨 Color Analysis")
    color_product_filter = st.selectbox(
        "Select Product for Color Analysis",
        options=["All"] + sorted(filtered_data['Product Title'].unique().tolist()),
        key="color_filter"
    )
    
    color_line_fig, color_pie_fig = create_distribution_charts(filtered_data, 'Color', color_product_filter)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(color_line_fig, use_container_width=True)
    with col2:
        st.plotly_chart(color_pie_fig, use_container_width=True)

    # Size Analysis
    st.subheader("📏 Size Analysis")
    size_product_filter = st.selectbox(
        "Select Product for Size Analysis",
        options=["All"] + sorted(filtered_data['Product Title'].unique().tolist()),
        key="size_filter"
    )

    size_line_fig, size_pie_fig = create_distribution_charts(filtered_data, 'Size', size_product_filter)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(size_line_fig, use_container_width=True)
    with col2:
        st.plotly_chart(size_pie_fig, use_container_width=True)

def create_dynamic_pivot(data, rows, values_col='Sales Dollars'):
    """
    Create a dynamic pivot table based on selected dimensions.
    
    Args:
        data (pd.DataFrame): The filtered dataset
        rows (list): List of dimensions to use as rows (e.g., ['Retailer', 'Product Title'])
        values_col (str): Column to aggregate ('Sales Dollars' or 'Units Sold')
    
    Returns:
        pd.DataFrame: Formatted pivot table with totals and percentages
    """
    # Create the base pivot table
    pivot = pd.pivot_table(
        data,
        values=values_col,
        index=rows,
        aggfunc='sum',
        margins=True,
        margins_name='Total'
    )
    
    # Calculate percentage of total
    total = pivot.loc['Total']
    pivot_pct = pivot.div(total).multiply(100)
    
    # Combine the values and percentages
    result = pd.DataFrame()
    result[values_col] = pivot
    result['% of Total'] = pivot_pct
    
    # Format the values
    if values_col == 'Sales Dollars':
        result[values_col] = result[values_col].map('${:,.2f}'.format)
    else:
        result[values_col] = result[values_col].map('{:,.0f}'.format)
    
    result['% of Total'] = result['% of Total'].map('{:.1f}%'.format)
    
    return result.reset_index()

# Add to visualizations.py

def create_pivot_analysis(data):
    """Create an interactive pivot table analysis section."""
    st.subheader("📊 Interactive Pivot Analysis")
    
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
    
    # Apply filters to create filtered_data
    filtered_data = data.copy()
    if "All" not in retailer_filter:
        filtered_data = filtered_data[filtered_data['Retailer'].isin(retailer_filter)]
    if "All" not in product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(product_filter)]
    
    # Define available dimensions and metrics
    dimensions = ['Retailer', 'Product Title', 'Color', 'Size']
    
    # Create three columns for pivot controls
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_rows = st.multiselect(
            "Select Row Dimensions",
            options=dimensions,
            default=['Retailer'],
            help="Select one or more dimensions to analyze. They will be nested in the order selected."
        )
    
    with col2:
        metric = st.radio(
            "Select Metric",
            options=['Sales Dollars', 'Units Sold'],
            horizontal=True
        )
    
    # Create pivot table if dimensions are selected
    if selected_rows:
        # Ensure numeric type for the metric column
        filtered_data[metric] = pd.to_numeric(filtered_data[metric], errors='coerce')
        
        # Create pivot table
        pivot_data = pd.pivot_table(
            filtered_data,
            values=metric,
            index=selected_rows,
            aggfunc='sum',
            margins=True,
            margins_name='Total'
        ).reset_index()
        
        # Calculate percentage of total
        total = pivot_data.loc[pivot_data[selected_rows[0]] == 'Total', metric].values[0]
        pivot_data['% of Total'] = (pivot_data[metric] / total * 100)
        
        # Sort by metric in descending order, keeping Total row at the bottom
        non_total = pivot_data[pivot_data[selected_rows[0]] != 'Total'].copy()
        total_row = pivot_data[pivot_data[selected_rows[0]] == 'Total'].copy()
        
        non_total = non_total.sort_values(by=metric, ascending=False)
        pivot_data = pd.concat([non_total, total_row], ignore_index=True)
        
        # Create a copy for display that maintains numeric sorting
        display_data = pivot_data.copy()
        
        # Format the values based on the metric type
        if metric == 'Sales Dollars':
            display_data = display_data.style.format({
                metric: '${:,.2f}',
                '% of Total': '{:.1f}%'
            })
        else:
            display_data = display_data.style.format({
                metric: '{:,.0f}',
                '% of Total': '{:.1f}%'
            })
        
        # Display the pivot table
        st.dataframe(
            display_data,
            use_container_width=True,
            height=400
        )
        
        # Add download button for the pivot data
        csv = pivot_data.to_csv(index=False)
        st.download_button(
            label="Download Pivot Data",
            data=csv,
            file_name=f"pivot_analysis_{'-'.join(selected_rows)}.csv",
            mime="text/csv"
        )
    else:
        st.info("Please select at least one dimension for analysis")
