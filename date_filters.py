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
        
    # Always use the most recent valid dates for both weekly and monthly views
    return valid_starts[-1], valid_ends[-1]

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
        
        # Find all valid week start dates
        current_date = min_date
        while current_date <= max_date:
            weekday = current_date.weekday() if start_on_monday else current_date.isoweekday() % 7
            if weekday == 0:  # Monday (or Sunday if start_on_monday is False)
                valid_starts.append(current_date)
            current_date += timedelta(days=1)
        
        # Find all valid week end dates
        current_date = min_date
        while current_date <= max_date:
            weekday = current_date.weekday() if start_on_monday else current_date.isoweekday() % 7
            if weekday == 6:  # Sunday (or Saturday if start_on_monday is False)
                valid_ends.append(current_date)
            current_date += timedelta(days=1)
        
        # If the last date in the data isn't a week end, add it as a valid end date
        if not valid_ends or valid_ends[-1] < max_date:
            valid_ends.append(max_date)
                    
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
    
    # Ensure we have at least one valid start and end date
    if not valid_starts:
        valid_starts = [min_date]
    if not valid_ends:
        valid_ends = [max_date]
    
    return valid_starts, valid_ends

def get_valid_end_dates(start_date, valid_ends):
    """Get all valid end dates that occur after the start date."""
    return [end_date for end_date in valid_ends if end_date >= start_date]

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
    
    if not valid_starts or not valid_ends:
        st.error("No valid date ranges found in the data")
        return min_date, max_date
    
    # Get default dates
    default_start, default_end = get_default_dates(valid_starts, valid_ends, min_date, max_date, view_type)
    
    # Create date filter UI
    st.write("### Select Date Range")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if view_type == 'Weekly':
            start_label = "Start Week (Select a Monday)" if start_on_monday else "Start Week (Select a Monday)"
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
            end_label = "End Week (Select a Monday)" if start_on_monday else "End Week (Select a Saturday)"
        else:
            end_label = "End Month"
        
        # Get valid end dates based on selected start date
        valid_end_dates = get_valid_end_dates(start_date, valid_ends)
        if not valid_end_dates:
            valid_end_dates = [max_date]
        
        end_date = st.date_input(
            end_label,
            value=valid_end_dates[0],
            min_value=start_date,
            max_value=max_date,
            key=f"{key_prefix}_end_date"
        )
        
        # If selected date isn't a valid end date, find the nearest one
        if end_date not in valid_end_dates:
            nearest_end = min(valid_end_dates, key=lambda x: abs((x - end_date).days))
            st.warning(f"Selected date adjusted to nearest valid {view_type.lower()} end: {nearest_end}")
            end_date = nearest_end
    
    return start_date, end_date

def filter_data_by_dates(data, start_date, end_date):
    """Filter DataFrame based on date range."""
    if start_date is None or end_date is None:
        return data
        
    return data[
        (data['Date'].dt.date >= start_date) &
        (data['Date'].dt.date <= end_date)
    ]
