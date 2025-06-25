# executive_summary.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_executive_metrics(data, date_range=None):
    """
    Calculate executive summary metrics for the specified date range.
    
    Args:
        data (pd.DataFrame): Sales data
        date_range (tuple): Optional tuple of (start_date, end_date)
        
    Returns:
        dict: Dictionary containing calculated metrics
    """
    if date_range:
        filtered_data = data[
            (data['Date'].dt.date >= date_range[0]) &
            (data['Date'].dt.date <= date_range[1])
        ]
    else:
        filtered_data = data
        
    # Calculate total sales
    total_sales = filtered_data['Sales Dollars'].sum()
    
    # Calculate active retailers (count unique retailers with sales > 0)
    active_retailers = filtered_data[
        filtered_data['Sales Dollars'] > 0
    ]['Retailer'].nunique()
    
    # Calculate average daily sales
    if not filtered_data.empty:
        date_min = filtered_data['Date'].dt.date.min()
        date_max = filtered_data['Date'].dt.date.max()
        days_diff = (date_max - date_min).days + 1  # Include both start and end dates
        avg_daily_sales = total_sales / days_diff
    else:
        avg_daily_sales = 0
    
    return {
        'total_sales': total_sales,
        'active_retailers': active_retailers,
        'avg_daily_sales': avg_daily_sales,
        'date_range': f"{date_min:%Y-%m-%d} to {date_max:%Y-%m-%d}" if not filtered_data.empty else "No data"
    }

def display_executive_summary(metrics):
    """
    Display executive summary metrics in a modern card layout.
    
    Args:
        metrics (dict): Dictionary containing the metrics to display
    """
    # Custom CSS for modern card styling
    st.markdown("""
        <style>
        .executive-metric-container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metric-header {
            color: #333333;
            font-size: 0.9em;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .metric-value {
            color: #1f1f1f;
            font-size: 1.8em;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .metric-subtext {
            color: #666666;
            font-size: 0.8em;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create the metrics container
    st.markdown('<div class="executive-metric-container">', unsafe_allow_html=True)
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-header">Total Sales</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">${metrics["total_sales"]:,.2f}</div>', 
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="metric-subtext">Period: {metrics["date_range"]}</div>',
            unsafe_allow_html=True
        )
        
    with col2:
        st.markdown('<div class="metric-header">Active Retailers</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{metrics["active_retailers"]}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="metric-subtext">With sales in period</div>',
            unsafe_allow_html=True
        )
        
    with col3:
        st.markdown('<div class="metric-header">Average Daily Sales</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">${metrics["avg_daily_sales"]:,.2f}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="metric-subtext">Per day in period</div>',
            unsafe_allow_html=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)