# summary_generator.py

import pandas as pd
import numpy as np
import streamlit as st
from typing import List, Dict, Tuple

def analyze_performance(data: pd.DataFrame, 
                       start_date: pd.Timestamp, 
                       end_date: pd.Timestamp, 
                       view_type: str = 'Weekly') -> str:
    """Analyze retailer performance and generate a summary."""
    
    # Calculate date ranges
    if view_type == 'Monthly':
        months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        previous_start = start_date - pd.DateOffset(months=months_diff)
        previous_end = end_date - pd.DateOffset(months=months_diff)
    else:
        days_diff = (end_date - start_date).days
        if days_diff == 6:  # Weekly view
            previous_start = start_date - pd.Timedelta(days=7)
            previous_end = end_date - pd.Timedelta(days=7)
        else:
            previous_start = start_date - pd.Timedelta(days=days_diff + 1)
            previous_end = start_date - pd.Timedelta(days=1)

    # Get period data
    current_data = data[
        (data['Date'].dt.date >= start_date.date()) &
        (data['Date'].dt.date <= end_date.date())
    ]
    previous_data = data[
        (data['Date'].dt.date >= previous_start.date()) &
        (data['Date'].dt.date <= previous_end.date())
    ]

    # Calculate retailer performance
    current_sales = current_data.groupby('Retailer')['Sales Dollars'].sum()
    previous_sales = previous_data.groupby('Retailer')['Sales Dollars'].sum()

    # Get all unique retailers across both periods
    all_retailers = pd.Index(set(current_sales.index) | set(previous_sales.index))
    
    # Create DataFrame with all retailers
    perf_df = pd.DataFrame(index=all_retailers)
    perf_df['Current Sales'] = current_sales
    perf_df['Previous Sales'] = previous_sales
    perf_df = perf_df.fillna(0)
    
    # Filter out retailers with less than $1,000 in sales in both periods
    perf_df = perf_df[
        (perf_df['Current Sales'] >= 1000) | 
        (perf_df['Previous Sales'] >= 1000)
    ]
    
    # If no retailers meet the threshold, return early
    if perf_df.empty:
        return "No retailers met the minimum sales threshold of $1,000 in either period."
    
    # Identify new/lost retailers
    new_retailers = list(perf_df[
        (perf_df['Current Sales'] > 0) & 
        (perf_df['Previous Sales'] == 0)
    ].index)
    lost_retailers = list(perf_df[
        (perf_df['Current Sales'] == 0) & 
        (perf_df['Previous Sales'] > 0)
    ].index)
    
    # Calculate percentage changes for existing retailers
    existing_retailers = perf_df[
        (perf_df['Current Sales'] > 0) & 
        (perf_df['Previous Sales'] > 0)
    ].index
    
    perf_df['Change %'] = np.nan  # Initialize with NaN
    if not existing_retailers.empty:
        perf_df.loc[existing_retailers, 'Change %'] = (
            (perf_df.loc[existing_retailers, 'Current Sales'] - 
             perf_df.loc[existing_retailers, 'Previous Sales']) / 
            perf_df.loc[existing_retailers, 'Previous Sales'] * 100
        ).round(1)

    # Get significant changes (>=10% change) for existing retailers
    significant = perf_df[
        (abs(perf_df['Change %']) >= 10) & 
        perf_df.index.isin(existing_retailers)
    ].copy()

    # Initialize summary lines
    lines = []

    # Process increases
    increases = significant[significant['Change %'] > 0]
    increases_retailers = list(increases.index)

    # Create a list to store retailers and their information for sorting
    increase_entries = []

    # Process retailers with significant increases
    for retailer in increases_retailers:
        sales = perf_df.loc[retailer, 'Current Sales']
        pct_change = perf_df.loc[retailer, 'Change %']
        
        retailer_current = current_data[current_data['Retailer'] == retailer]
        retailer_prev = previous_data[previous_data['Retailer'] == retailer]
        
        # Get product performance
        current_products = retailer_current.groupby('Product Title')['Sales Dollars'].sum()
        prev_products = retailer_prev.groupby('Product Title')['Sales Dollars'].sum()
        
        # Calculate product changes
        product_changes = pd.DataFrame({
            'Current Sales': current_products,
            'Previous Sales': prev_products
        }).fillna(0)
        
        product_changes['Change'] = product_changes['Current Sales'] - product_changes['Previous Sales']
        product_changes['Change %'] = (
            (product_changes['Current Sales'] - product_changes['Previous Sales']) /
            product_changes['Previous Sales'].replace(0, np.nan) * 100
        ).round(1)
        
        # Get top 3 products by change
        significant_products = product_changes[
            product_changes['Change'] > 0
        ].nlargest(3, 'Change')
        
        # Format product texts
        product_texts = []
        for name, row in significant_products.iterrows():
            if row['Previous Sales'] == 0:
                change_text = "new"
            else:
                change_text = f"up {row['Change %']:.1f}%"
            product_texts.append(f"{name} (${row['Current Sales']:,.0f}, {change_text})")
        
        # Format product section
        if product_texts:
            if len(product_texts) == 1:
                product_section = f" - This was driven by {product_texts[0]}"
            elif len(product_texts) == 2:
                product_section = f" - This was driven by {product_texts[0]} and {product_texts[1]}"
            else:
                product_section = f" - This was driven by {product_texts[0]}, {product_texts[1]}, and {product_texts[2]}"
        else:
            product_section = " - No individual products showed significant increases"
        
        line = f"• {retailer} (${sales:,.0f}) was up {pct_change:.1f}% vs the previous period{product_section}.\n"
        increase_entries.append((sales, line))

    # Process new retailers
    for retailer in new_retailers:
        sales = perf_df.loc[retailer, 'Current Sales']
        retailer_current = current_data[current_data['Retailer'] == retailer]
        
        # Show top 3 products
        top_products = retailer_current.groupby('Product Title')['Sales Dollars'].sum().nlargest(3)
        
        product_texts = []
        for name, sales_value in top_products.items():
            product_texts.append(f"{name} (${sales_value:,.0f}, new)")
        
        # Format product section
        if product_texts:
            if len(product_texts) == 1:
                product_section = f" - Top product: {product_texts[0]}"
            elif len(product_texts) == 2:
                product_section = f" - Top products: {product_texts[0]} and {product_texts[1]}"
            else:
                product_section = f" - Top products: {product_texts[0]}, {product_texts[1]}, and {product_texts[2]}"
        else:
            product_section = ""
        
        line = f"• {retailer} (${sales:,.0f}) was new this period{product_section}.\n"
        increase_entries.append((sales, line))

    # Sort and append increases
    if increase_entries:
        lines.append("The following retailers (with ≥$1,000 in sales) showed significant increases:\n\n")
        increase_entries.sort(reverse=True)  # Sort by sales in descending order
        lines.extend(line for _, line in increase_entries)

    # Process decreases
    decreases = significant[significant['Change %'] < 0]
    decrease_entries = []

    # Process retailers with significant decreases
    for retailer in decreases.index:
        sales = perf_df.loc[retailer, 'Current Sales']
        pct_change = abs(perf_df.loc[retailer, 'Change %'])
        
        retailer_current = current_data[current_data['Retailer'] == retailer]
        retailer_prev = previous_data[previous_data['Retailer'] == retailer]
        
        # Calculate product changes
        current_products = retailer_current.groupby('Product Title')['Sales Dollars'].sum()
        prev_products = retailer_prev.groupby('Product Title')['Sales Dollars'].sum()
        
        product_changes = pd.DataFrame({
            'Current Sales': current_products,
            'Previous Sales': prev_products
        }).fillna(0)
        
        product_changes['Change'] = product_changes['Current Sales'] - product_changes['Previous Sales']
        product_changes['Change %'] = (
            (product_changes['Current Sales'] - product_changes['Previous Sales']) /
            product_changes['Previous Sales'].replace(0, np.nan) * 100
        ).round(1)
        
        # Get significant decreases
        significant_products = product_changes[
            product_changes['Change'] < 0
        ].nsmallest(3, 'Change')
        
        # Format product texts
        product_texts = []
        for name, row in significant_products.iterrows():
            if row['Current Sales'] == 0:
                change_text = f"no sales (was ${row['Previous Sales']:,.0f})"
            else:
                change_text = f"down {abs(row['Change %']):.1f}%"
            product_texts.append(f"{name} (${row['Current Sales']:,.0f}, {change_text})")
        
        # Format product section
        if product_texts:
            if len(product_texts) == 1:
                product_section = f" - This was driven by {product_texts[0]}"
            elif len(product_texts) == 2:
                product_section = f" - This was driven by {product_texts[0]} and {product_texts[1]}"
            else:
                product_section = f" - This was driven by {product_texts[0]}, {product_texts[1]}, and {product_texts[2]}"
        else:
            product_section = " - No individual products showed significant decreases"
        
        line = f"• {retailer} (${sales:,.0f}) was down {pct_change:.1f}% vs the previous period{product_section}.\n"
        decrease_entries.append((sales, line))

    # Process lost retailers
    for retailer in lost_retailers:
        prev_sales = perf_df.loc[retailer, 'Previous Sales']
        retailer_prev = previous_data[previous_data['Retailer'] == retailer]
        
        # Show top 3 products from previous period
        top_products = retailer_prev.groupby('Product Title')['Sales Dollars'].sum().nlargest(3)
        
        product_texts = []
        for name, sales_value in top_products.items():
            product_texts.append(f"{name} (${sales_value:,.0f} previous period)")
        
        # Format product section
        if product_texts:
            if len(product_texts) == 1:
                product_section = f" - Main lost product was {product_texts[0]}"
            elif len(product_texts) == 2:
                product_section = f" - Main lost products were {product_texts[0]} and {product_texts[1]}"
            else:
                product_section = f" - Main lost products were {product_texts[0]}, {product_texts[1]}, and {product_texts[2]}"
        else:
            product_section = ""
        
        line = f"• {retailer} (${prev_sales:,.0f} previous period) had no sales this period{product_section}.\n"
        decrease_entries.append((prev_sales, line))

    # Sort and append decreases
    if decrease_entries:
        lines.append("\nThe following retailers (with ≥$1,000 in sales) showed significant decreases:\n\n")
        decrease_entries.sort(reverse=True)  # Sort by sales in descending order
        lines.extend(line for _, line in decrease_entries)

    # Check if there were any significant changes
    if (len(increases_retailers) == 0 and len(new_retailers) == 0 and 
        len(decreases.index) == 0 and len(lost_retailers) == 0):
        return "No retailers with ≥$1,000 in sales showed significant changes (≥10%) in revenue compared to the previous period."

    return ''.join(lines)

def display_performance_summary(data: pd.DataFrame, date_range: tuple, view_type: str = 'Weekly'):
    """Display the performance summary in Streamlit."""
    summary = analyze_performance(
        data,
        pd.to_datetime(date_range[0]),
        pd.to_datetime(date_range[1]),
        view_type
    )
    
    st.subheader("📊 Performance Summary")
    
    with st.expander("View Summary", expanded=False):
        st.text(summary)
        
        st.caption(
            f"Analysis comparing {date_range[0]} to {date_range[1]} "
            f"with the previous {view_type.lower()} period."
        )