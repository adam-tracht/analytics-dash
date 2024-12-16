# inventory_visualizations.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import timedelta

def calculate_inventory_metrics(inventory_data, sales_data, filters):
    """
    Calculate inventory metrics including WOS based on different historical periods.
    
    Args:
        inventory_data (pd.DataFrame): Inventory data with columns Date, OH Qty, SKU
        sales_data (pd.DataFrame): Sales data with columns Date, Units Sold, Product SKU
        filters (dict): Dictionary containing filter values for category, product, color, size
        
    Returns:
        dict: Dictionary containing calculated metrics
    """
    import pandas as pd
    
    # Get most recent inventory snapshot
    latest_date = inventory_data['Date'].max()
    latest_inventory = inventory_data[inventory_data['Date'] == latest_date].copy()
    
    # Apply filters to inventory data
    filtered_inventory = latest_inventory.copy()
    filtered_sales = sales_data.copy()
    
    # Safely apply filters only when columns exist
    def safe_filter(df, column, filter_value):
        """Apply filter only if column exists in dataframe"""
        if column in df.columns and filter_value != "All":
            return df[df[column] == filter_value]
        return df
    
    # Apply each filter if it exists and has a value
    if filters.get('category'):
        filtered_inventory = safe_filter(filtered_inventory, 'Category', filters['category'])
        # Only filter sales data by category if the column exists
        if 'Category' in filtered_sales.columns:
            filtered_sales = safe_filter(filtered_sales, 'Category', filters['category'])
    
    if filters.get('product'):
        filtered_inventory = safe_filter(filtered_inventory, 'Product Title', filters['product'])
        filtered_sales = safe_filter(filtered_sales, 'Product Title', filters['product'])
    
    if filters.get('color'):
        filtered_inventory = safe_filter(filtered_inventory, 'Color', filters['color'])
        filtered_sales = safe_filter(filtered_sales, 'Color', filters['color'])
    
    if filters.get('size'):
        filtered_inventory = safe_filter(filtered_inventory, 'Size', filters['size'])
        filtered_sales = safe_filter(filtered_sales, 'Size', filters['size'])
    
    # Calculate total units and SKUs for filtered data
    total_units = filtered_inventory['OH Qty'].sum()
    total_skus = filtered_inventory['SKU'].nunique()
    
    # Calculate weekly sales rates for different periods using filtered data
    current_date = filtered_sales['Date'].max()
    
    def calculate_weekly_sales_rate(days):
        """Calculate average weekly sales rate over a specified period."""
        start_date = current_date - pd.Timedelta(days=days)
        period_sales = filtered_sales[filtered_sales['Date'] > start_date]['Units Sold'].sum()
        weeks = days / 7
        return period_sales / weeks if weeks > 0 else 0
    
    # Calculate sales rates for different periods
    weekly_sales_rate_1w = calculate_weekly_sales_rate(7)   # 1 week
    weekly_sales_rate_4w = calculate_weekly_sales_rate(28)  # 4 weeks
    weekly_sales_rate_12w = calculate_weekly_sales_rate(84) # 12 weeks
    
    # Calculate WOS for different periods
    def calculate_wos(weekly_rate):
        """Calculate weeks of supply based on weekly sales rate."""
        return total_units / weekly_rate if weekly_rate > 0 else float('inf')
    
    wos_1w = calculate_wos(weekly_sales_rate_1w)
    wos_4w = calculate_wos(weekly_sales_rate_4w)
    wos_12w = calculate_wos(weekly_sales_rate_12w)
    
    # Calculate SKU-level metrics for filtered data
    sku_metrics = []
    for sku in filtered_inventory['SKU'].unique():
        sku_oh = filtered_inventory[filtered_inventory['SKU'] == sku]['OH Qty'].sum()
        sku_sales = filtered_sales[
            (filtered_sales['Product SKU'] == sku) & 
            (filtered_sales['Date'] > current_date - pd.Timedelta(days=28))
        ]['Units Sold'].sum()
        
        weekly_rate = sku_sales / 4  # 4-week average
        wos = sku_oh / weekly_rate if weekly_rate > 0 else float('inf')
        
        sku_metrics.append({
            'SKU': sku,
            'OH Qty': sku_oh,
            'WOS': min(wos, 99.0)  # Cap at 99 weeks for display
        })
    
    return {
        'total_units': total_units,
        'total_skus': total_skus,
        'wos_1w': min(wos_1w, 99.0),
        'wos_4w': min(wos_4w, 99.0),
        'wos_12w': min(wos_12w, 99.0),
        'sku_metrics': sku_metrics,
        'weekly_rates': {
            '1w': weekly_sales_rate_1w,
            '4w': weekly_sales_rate_4w,
            '12w': weekly_sales_rate_12w
        }
    }

def display_inventory_metrics(inventory_data, sales_data, filters):
    """Display enhanced inventory metrics using multiple time periods."""
    metrics = calculate_inventory_metrics(inventory_data, sales_data, filters)
    
    # Display overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Units On Hand", f"{int(metrics['total_units']):,}")
    
    with col2:
        st.metric("Total SKUs", f"{metrics['total_skus']:,}")
    
    with col3:
        st.metric("WOS (4-week avg)", f"{metrics['wos_4w']:.1f}")
        st.caption(f"Weekly Rate: {metrics['weekly_rates']['4w']:.1f} units")
    
    with col4:
        st.metric("WOS (12-week avg)", f"{metrics['wos_12w']:.1f}")
        st.caption(f"Weekly Rate: {metrics['weekly_rates']['12w']:.1f} units")
    
    # Display SKU-level metrics in an expandable section
    with st.expander("SKU-Level Metrics", expanded=True):
        if metrics['sku_metrics']:
            # Create selection columns for pivot dimensions
            col1, col2 = st.columns([2, 2])
            
            with col1:
                pivot_dimensions = st.multiselect(
                    "Select Dimensions",
                    options=['Product Title', 'Color', 'Size', 'SKU'],
                    default=['Product Title', 'Color', 'Size'],
                    key="sku_pivot_dimensions"
                )
            
            # Get the latest inventory snapshot
            latest_date = inventory_data['Date'].max()
            latest_inventory = inventory_data[inventory_data['Date'] == latest_date].copy()
            
            # Create pivot table
            if pivot_dimensions:
                pivot_data = latest_inventory.pivot_table(
                    values=['OH Qty'],
                    index=pivot_dimensions,
                    aggfunc='sum',
                    margins=True,
                    margins_name='Total'
                ).reset_index()
                
                # Sort by OH Qty descending (keep Total row at bottom)
                non_total = pivot_data[pivot_data[pivot_dimensions[0]] != 'Total'].sort_values('OH Qty', ascending=False)
                total_row = pivot_data[pivot_data[pivot_dimensions[0]] == 'Total']
                pivot_data = pd.concat([non_total, total_row])
                
                # Calculate WOS for each row
                def calculate_wos(row):
                    if row[pivot_dimensions[0]] == 'Total':
                        return metrics['wos_4w']
                    
                    # Find matching SKUs based on the selected dimensions
                    mask = pd.Series(True, index=latest_inventory.index)
                    for dim in pivot_dimensions:
                        mask &= latest_inventory[dim] == row[dim]
                    
                    matching_skus = latest_inventory[mask]['SKU'].unique()
                    
                    if len(matching_skus) == 0:
                        return None
                    
                    # Calculate average WOS for all matching SKUs
                    matching_wos = []
                    for sku in matching_skus:
                        sku_metrics = next(
                            (item for item in metrics['sku_metrics'] if item['SKU'] == sku),
                            None
                        )
                        if sku_metrics:
                            matching_wos.append(sku_metrics['WOS'])
                    
                    return np.mean(matching_wos) if matching_wos else None
                
                pivot_data['WOS (4-week)'] = pivot_data.apply(calculate_wos, axis=1)
                
                # Reorder columns
                cols_order = pivot_dimensions.copy()
                cols_order.extend(['OH Qty', 'WOS (4-week)'])
                
                # Format and display the pivot table
                st.dataframe(
                    pivot_data[cols_order].style.format({
                        'OH Qty': '{:,.0f}',
                        'WOS (4-week)': '{:.1f}'
                    }).background_gradient(
                        cmap='RdYlGn',
                        subset=['WOS (4-week)'],
                        vmin=0,
                        vmax=12
                    ),
                    use_container_width=True
                )
                
                # Add download button
                csv = pivot_data[cols_order].to_csv(index=False)
                st.download_button(
                    label="Download SKU Analysis",
                    data=csv,
                    file_name="sku_level_analysis.csv",
                    mime="text/csv"
                )
            else:
                st.info("Please select at least one dimension for analysis")
    
    # Add date context
    st.caption(f"Inventory metrics as of {inventory_data['Date'].max().strftime('%Y-%m-%d')}")

def create_inventory_treemap(inventory_data):
    """Create a treemap visualization of inventory levels."""
    treemap_data = inventory_data.groupby(['Category', 'Product Title']).agg({
        'OH Qty': 'sum'
    }).reset_index()
    
    fig = px.treemap(
        treemap_data,
        path=['Category', 'Product Title'],
        values='OH Qty',
        title='Inventory Levels Hierarchy',
        height=500
    )
    
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Units: %{value:,.0f}<extra></extra>"
    )
    
    fig.update_layout(
        template='plotly_white'
    )
    
    return fig

def create_historical_inventory_chart(inventory_data, filters):
    """Create a line chart showing inventory levels over time with filters."""
    filtered_data = inventory_data.copy()
    
    # Apply filters
    if filters.get('category') and filters['category'] != "All":
        filtered_data = filtered_data[filtered_data['Category'] == filters['category']]
    if filters.get('product') and filters['product'] != "All":
        filtered_data = filtered_data[filtered_data['Product Title'] == filters['product']]
    if filters.get('color') and filters['color'] != "All":
        filtered_data = filtered_data[filtered_data['Color'] == filters['color']]
    if filters.get('size') and filters['size'] != "All":
        filtered_data = filtered_data[filtered_data['Size'] == filters['size']]
    
    # Group by date
    daily_inventory = filtered_data.groupby('Date')['OH Qty'].sum().reset_index()
    
    # Calculate sell-through metrics for the filtered data
    latest_date = daily_inventory['Date'].max()
    earliest_date = daily_inventory['Date'].min()
    latest_qty = daily_inventory[daily_inventory['Date'] == latest_date]['OH Qty'].iloc[0]
    initial_qty = daily_inventory[daily_inventory['Date'] == earliest_date]['OH Qty'].iloc[0]
    
    days_between = (latest_date - earliest_date).days
    weeks_between = max(1, days_between / 7)
    
    units_sold = initial_qty - latest_qty
    sell_through_rate = (units_sold / initial_qty * 100) if initial_qty > 0 else 0
    weekly_sell_through = sell_through_rate / weeks_between
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_inventory['Date'],
        y=daily_inventory['OH Qty'],
        mode='lines',
        name='Inventory Level',
        line=dict(color='#4B90B0', width=2),
        hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>" +
                     "<b>Units:</b> %{y:,.0f}<extra></extra>"
    ))
    
    # Add annotations for sell-through metrics
    fig.add_annotation(
        x=0.02,
        y=1.1,
        xref="paper",
        yref="paper",
        text=f"Period Sell-Through: {sell_through_rate:.1f}%<br>Weekly Sell-Through: {weekly_sell_through:.1f}%",
        showarrow=False,
        font=dict(size=12),
        align="left"
    )
    
    fig.update_layout(
        title='Historical Inventory Levels',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Units On Hand'),
        template='plotly_white',
        height=400,
        margin=dict(t=100)
    )
    
    return fig

def display_inventory_filters(inventory_data):
    """Display filters for inventory analysis with cascading options."""
    filtered_data = inventory_data.copy()
    
    # Create columns for filters
    col1, col2, col3, col4 = st.columns(4)
    
    # Category filter
    with col1:
        categories = ["All"] + sorted(inventory_data['Category'].unique().tolist())
        category_filter = st.selectbox(
            "📦 Category",
            options=categories
        )
        
        # Apply category filter to data
        if category_filter != "All":
            filtered_data = filtered_data[filtered_data['Category'] == category_filter]
    
    # Product filter - options depend on category
    with col2:
        if category_filter != "All":
            available_products = filtered_data['Product Title'].unique()
        else:
            available_products = inventory_data['Product Title'].unique()
            
        products = ["All"] + sorted(available_products.tolist())
        product_filter = st.selectbox(
            "🏷️ Product",
            options=products
        )
        
        # Apply product filter to data
        if product_filter != "All":
            filtered_data = filtered_data[filtered_data['Product Title'] == product_filter]
    
    # Color filter - options depend on category and product
    with col3:
        available_colors = filtered_data['Color'].unique()
        colors = ["All"] + sorted([c for c in available_colors if pd.notna(c) and str(c).strip() != ''])
        color_filter = st.selectbox(
            "🎨 Color",
            options=colors
        )
        
        # Apply color filter to data
        if color_filter != "All":
            filtered_data = filtered_data[filtered_data['Color'] == color_filter]
    
    # Size filter - options depend on all previous filters
    with col4:
        available_sizes = filtered_data['Size'].unique()
        sizes = ["All"] + sorted([s for s in available_sizes if pd.notna(s) and str(s).strip() != ''])
        size_filter = st.selectbox(
            "📏 Size",
            options=sizes
        )
        
        # Apply size filter to data
        if size_filter != "All":
            filtered_data = filtered_data[filtered_data['Size'] == size_filter]
    
    # Create filters dictionary
    filters = {
        'category': category_filter,
        'product': product_filter,
        'color': color_filter,
        'size': size_filter
    }
    
    return filtered_data, filters

def create_inventory_by_category(inventory_data):
    """Create inventory distribution visualization by category."""
    # Group data by category
    category_data = inventory_data.groupby('Category').agg({
        'OH Qty': 'sum',
        'SKU': 'nunique'
    }).reset_index()
    
    # Calculate percentages
    total_qty = category_data['OH Qty'].sum()
    category_data['Percentage'] = (category_data['OH Qty'] / total_qty * 100).round(1)
    
    # Create figure
    fig = go.Figure()
    
    # Add bars for quantity
    fig.add_trace(go.Bar(
        x=category_data['Category'],
        y=category_data['OH Qty'],
        name='Units On Hand',
        marker_color='#4B90B0',
        hovertemplate="<b>Category:</b> %{x}<br>" +
                     "<b>Units:</b> %{y:,.0f}<br>" +
                     "<b>Percentage:</b> %{text}%<extra></extra>",
        text=category_data['Percentage'].apply(lambda x: f"{x:.1f}")
    ))
    
    # Add line for SKU count
    fig.add_trace(go.Scatter(
        x=category_data['Category'],
        y=category_data['SKU'],
        name='Number of SKUs',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#FF6B6B', width=2),
        marker=dict(size=8),
        hovertemplate="<b>Category:</b> %{x}<br>" +
                     "<b>SKUs:</b> %{y:,.0f}<extra></extra>"
    ))
    
    fig.update_layout(
        title='Inventory Distribution by Category',
        xaxis=dict(title='Category', tickangle=45),
        yaxis=dict(title='Units On Hand', gridcolor='rgba(211,211,211,0.3)'),
        yaxis2=dict(
            title='Number of SKUs',
            overlaying='y',
            side='right',
            gridcolor='rgba(211,211,211,0.3)'
        ),
        hovermode='x unified',
        template='plotly_white',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_inventory_treemap(inventory_data):
    """Create a treemap visualization of inventory levels."""
    treemap_data = inventory_data.groupby(['Category', 'Product Title']).agg({
        'OH Qty': 'sum'
    }).reset_index()
    
    fig = px.treemap(
        treemap_data,
        path=['Category', 'Product Title'],
        values='OH Qty',
        title='Inventory Levels Hierarchy',
        height=500
    )
    
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Units: %{value:,.0f}<extra></extra>"
    )
    
    fig.update_layout(
        template='plotly_white'
    )
    
    return fig

def create_historical_inventory_chart(inventory_data, filters):
    """Create a line chart showing inventory levels over time with filters."""
    filtered_data = inventory_data.copy()
    
    # Apply filters
    if filters.get('category') and filters['category'] != "All":
        filtered_data = filtered_data[filtered_data['Category'] == filters['category']]
    if filters.get('product') and filters['product'] != "All":
        filtered_data = filtered_data[filtered_data['Product Title'] == filters['product']]
    if filters.get('color') and filters['color'] != "All":
        filtered_data = filtered_data[filtered_data['Color'] == filters['color']]
    if filters.get('size') and filters['size'] != "All":
        filtered_data = filtered_data[filtered_data['Size'] == filters['size']]
    
    # Group by date
    daily_inventory = filtered_data.groupby('Date')['OH Qty'].sum().reset_index()
    
    # Calculate sell-through metrics for the filtered data
    latest_date = daily_inventory['Date'].max()
    earliest_date = daily_inventory['Date'].min()
    latest_qty = daily_inventory[daily_inventory['Date'] == latest_date]['OH Qty'].iloc[0]
    initial_qty = daily_inventory[daily_inventory['Date'] == earliest_date]['OH Qty'].iloc[0]
    
    days_between = (latest_date - earliest_date).days
    weeks_between = max(1, days_between / 7)
    
    units_sold = initial_qty - latest_qty
    sell_through_rate = (units_sold / initial_qty * 100) if initial_qty > 0 else 0
    weekly_sell_through = sell_through_rate / weeks_between
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_inventory['Date'],
        y=daily_inventory['OH Qty'],
        mode='lines',
        name='Inventory Level',
        line=dict(color='#4B90B0', width=2),
        hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>" +
                     "<b>Units:</b> %{y:,.0f}<extra></extra>"
    ))
    
    # Add annotations for sell-through metrics
    fig.add_annotation(
        x=0.02,
        y=1.1,
        xref="paper",
        yref="paper",
        text=f"Period Sell-Through: {sell_through_rate:.1f}%<br>Weekly Sell-Through: {weekly_sell_through:.1f}%",
        showarrow=False,
        font=dict(size=12),
        align="left"
    )
    
    fig.update_layout(
        title='Historical Inventory Levels',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Units On Hand'),
        template='plotly_white',
        height=400,
        margin=dict(t=100)
    )
    
    return fig

def display_inventory_filters(inventory_data):
    """Display filters for inventory analysis with cascading options."""
    filtered_data = inventory_data.copy()
    
    # Create columns for filters
    col1, col2, col3, col4 = st.columns(4)
    
    # Category filter
    with col1:
        categories = ["All"] + sorted(inventory_data['Category'].unique().tolist())
        category_filter = st.selectbox(
            "📦 Category",
            options=categories
        )
        
        # Apply category filter to data
        if category_filter != "All":
            filtered_data = filtered_data[filtered_data['Category'] == category_filter]
    
    # Product filter - options depend on category
    with col2:
        if category_filter != "All":
            available_products = filtered_data['Product Title'].unique()
        else:
            available_products = inventory_data['Product Title'].unique()
            
        products = ["All"] + sorted(available_products.tolist())
        product_filter = st.selectbox(
            "🏷️ Product",
            options=products
        )
        
        # Apply product filter to data
        if product_filter != "All":
            filtered_data = filtered_data[filtered_data['Product Title'] == product_filter]
    
    # Color filter - options depend on category and product
    with col3:
        available_colors = filtered_data['Color'].unique()
        colors = ["All"] + sorted([c for c in available_colors if pd.notna(c) and str(c).strip() != ''])
        color_filter = st.selectbox(
            "🎨 Color",
            options=colors
        )
        
        # Apply color filter to data
        if color_filter != "All":
            filtered_data = filtered_data[filtered_data['Color'] == color_filter]
    
    # Size filter - options depend on all previous filters
    with col4:
        available_sizes = filtered_data['Size'].unique()
        sizes = ["All"] + sorted([s for s in available_sizes if pd.notna(s) and str(s).strip() != ''])
        size_filter = st.selectbox(
            "📏 Size",
            options=sizes
        )
        
        # Apply size filter to data
        if size_filter != "All":
            filtered_data = filtered_data[filtered_data['Size'] == size_filter]
    
    # Create filters dictionary
    filters = {
        'category': category_filter,
        'product': product_filter,
        'color': color_filter,
        'size': size_filter
    }
    
    return filtered_data, filters

def clean_inventory_data(inventory_data):
    """Clean inventory data by handling missing values and standardizing formats."""
    cleaned_data = inventory_data.copy()
    
    # Convert OH Qty to numeric if not already
    cleaned_data['OH Qty'] = pd.to_numeric(cleaned_data['OH Qty'].astype(str).str.replace(',', ''), errors='coerce')
    
    # Clean dimension values
    for dimension in ['Color', 'Size']:
        cleaned_data[dimension] = cleaned_data[dimension].fillna('N/A')
        cleaned_data[dimension] = cleaned_data[dimension].replace(['', ' ', '0', '0.0', 'nan', 'None'], 'N/A')
        cleaned_data[dimension] = cleaned_data[dimension].astype(str).apply(lambda x: 'N/A' if x.strip() == '' else x)
    
    # Ensure dates are in datetime format
    cleaned_data['Date'] = pd.to_datetime(cleaned_data['Date'])
    
    return cleaned_data

def clean_inventory_data(inventory_data):
    """Clean inventory data by handling missing values and standardizing formats."""
    cleaned_data = inventory_data.copy()
    
    # Convert OH Qty to numeric if not already
    cleaned_data['OH Qty'] = pd.to_numeric(cleaned_data['OH Qty'].astype(str).str.replace(',', ''), errors='coerce')
    
    # Clean dimension values
    for dimension in ['Color', 'Size']:
        cleaned_data[dimension] = cleaned_data[dimension].fillna('N/A')
        cleaned_data[dimension] = cleaned_data[dimension].replace(['', ' ', '0', '0.0', 'nan', 'None'], 'N/A')
        cleaned_data[dimension] = cleaned_data[dimension].astype(str).apply(lambda x: 'N/A' if x.strip() == '' else x)
    
    # Ensure dates are in datetime format
    cleaned_data['Date'] = pd.to_datetime(cleaned_data['Date'])
    
    return cleaned_data