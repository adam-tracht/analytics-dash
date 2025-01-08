# date_filters.py

import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

def get_month_end(year, month, max_date):
    """Calculate the end of the month, ensuring it doesn't exceed max_date."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    month_end = next_month - timedelta(days=1)
    return min(month_end, max_date)

def get_default_dates(valid_starts, valid_ends, min_date, max_date, view_type='Weekly'):
    """
    Get sensible default start and end dates based on the view type.
    For weekly view, defaults to the most recent complete week.
    For monthly view, defaults to the most recent complete month.
    """
    if not valid_starts or not valid_ends:
        return min_date, max_date
        
    if view_type == 'Weekly':
        # Get the most recent start date that has a complete week of data
        for start_date in reversed(valid_starts):
            end_date = start_date + timedelta(days=6)
            if end_date <= max_date:
                return start_date, end_date
        # If no complete week found, use the earliest week
        return valid_starts[0], min(valid_ends[0], max_date)
    else:
        # For monthly view, use the most recent complete month
        return valid_starts[-1], min(valid_ends[-1], max_date)

def get_valid_dates(data, view_type='Weekly', start_on_monday=True):
    """
    Get valid start and end dates based on actual data points.
    Returns two lists of datetime.date objects representing valid start and end dates.
    """
    dates = sorted(data['Date'].dt.date.unique())
    min_date = min(dates)
    max_date = max(dates)
    
    if view_type == 'Weekly':
        valid_starts = []
        valid_ends = []
        
        for current_date in dates:
            # Check if this is a valid week start
            weekday = current_date.weekday() if start_on_monday else current_date.isoweekday() % 7
            if weekday == 0:  # Monday (or Sunday if start_on_monday is False)
                valid_starts.append(current_date)
                # Calculate the end date (Sunday) for this week, not exceeding max_date
                week_end = min(current_date + timedelta(days=6), max_date)
                valid_ends.append(week_end)
                    
    else:  # Monthly view
        valid_starts = []
        valid_ends = []
        
        # Group dates by year and month
        date_months = set((d.year, d.month) for d in dates)
        
        for year, month in sorted(date_months):
            # First day of month
            month_start = date(year, month, 1)
            if month_start >= min_date:
                valid_starts.append(month_start)
                # Calculate month end, ensuring it doesn't exceed max_date
                month_end = get_month_end(year, month, max_date)
                valid_ends.append(month_end)
    
    return valid_starts, valid_ends

def create_date_filter(data, view_type='Weekly', key_prefix=''):
    """
    Create a date filter component using a calendar picker that only allows selection
    of valid dates based on data points.
    """
    # Ensure we have a Date column
    if 'Date' not in data.columns:
        st.error("Data must contain a 'Date' column")
        return None, None
    
    # Ensure Date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(data['Date']):
        try:
            data['Date'] = pd.to_datetime(data['Date'])
        except Exception as e:
            st.error(f"Could not convert Date column to datetime: {str(e)}")
            return None, None
    
    min_date = data['Date'].min().date()
    max_date = data['Date'].max().date()
    
    # Week start preference in sidebar
    with st.sidebar:
        st.write("### Date Settings")
        start_on_monday = st.radio(
            "Week Starts On",
            options=["Monday", "Sunday"],
            index=0,
            key=f"{key_prefix}_week_start",
            format_func=lambda x: f"Weeks Start on {x}"
        ) == "Monday"
    
    # Get valid dates based on view type and preferences
    valid_starts, valid_ends = get_valid_dates(data, view_type, start_on_monday)
    
    if not valid_starts:
        st.error("No valid date ranges found in the data")
        st.write("Please check the data format and ensure there are complete weeks/months")
        return min_date, max_date
    
    # Get default dates
    default_start, default_end = get_default_dates(valid_starts, valid_ends, min_date, max_date, view_type)
    
    # Create date filter UI
    st.write("### Select Date Range")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if view_type == 'Weekly':
            start_label = "Start Week (Select a Monday)" if start_on_monday else "Start Week (Select a Sunday)"
        else:
            start_label = "Start Month"
        
        start_date = st.date_input(
            start_label,
            value=default_start,
            min_value=min_date,
            max_value=max_date,
            key=f"{key_prefix}_start_date"
        )
        
        # If selected date isn't valid, find the nearest valid date
        if start_date not in valid_starts:
            nearest_start = min(valid_starts, key=lambda x: abs((x - start_date).days))
            st.warning(f"Selected date adjusted to nearest valid {view_type.lower()} start: {nearest_start}")
            start_date = nearest_start
    
    with col2:
        if view_type == 'Weekly':
            end_label = "End Week (Select a Sunday)" if start_on_monday else "End Week (Select a Saturday)"
        else:
            end_label = "End Month"
        
        # Find the corresponding end date for the selected start date
        start_idx = valid_starts.index(start_date)
        valid_end_options = valid_ends[start_idx:]
        
        if not valid_end_options:
            valid_end_options = [valid_ends[-1]]
        
        end_date = st.date_input(
            end_label,
            value=default_end,
            min_value=start_date,
            max_value=max_date,
            key=f"{key_prefix}_end_date"
        )
        
        # If selected date isn't valid, find the nearest valid date
        if end_date not in valid_end_options:
            nearest_end = min(valid_end_options, key=lambda x: abs((x - end_date).days))
            st.warning(f"Selected date adjusted to nearest valid {view_type.lower()} end: {nearest_end}")
            end_date = nearest_end
    
    # Display selected range info
    if view_type == 'Weekly':
        week_text = "Monday" if start_on_monday else "Sunday"
        st.caption(
            f"Selected range: Week of {start_date.strftime('%Y-%m-%d')} ({week_text}) to "
            f"Week ending {end_date.strftime('%Y-%m-%d')}"
        )
    else:
        st.caption(
            f"Selected range: {start_date.strftime('%B %Y')} to {end_date.strftime('%B %Y')}"
        )
    
    return start_date, end_date

def filter_data_by_dates(data, start_date, end_date):
    """Filter DataFrame based on date range."""
    if start_date is None or end_date is None:
        return data
        
    return data[
        (data['Date'].dt.date >= start_date) &
        (data['Date'].dt.date <= end_date)
    ]