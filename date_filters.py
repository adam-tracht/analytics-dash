# date_filters.py

import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

def extend_data_with_future_record(data, view_type='Weekly'):
    """
    Extend the dataset by adding future records with zeros to allow proper date range selection.
    For weekly view: Adds one day after the last date
    For monthly view: Adds records through the end of the current month
    """
    if data.empty:
        return data
        
    # Get the most recent date in the data
    max_date = data['Date'].max()
    
    # Create a template row by taking the most recent row
    template_row = data.iloc[-1].copy()
    
    # Initialize list to hold new rows
    new_rows = []
    
    if view_type == 'Monthly':
        # Calculate the end of the current month
        month_end = get_month_end(max_date.year, max_date.month)
        
        # Add a row for each remaining day in the month
        current_date = max_date + pd.Timedelta(days=1)
        while current_date.date() <= month_end:
            new_row = template_row.copy()
            new_row['Date'] = current_date
            new_rows.append(new_row)
            current_date += pd.Timedelta(days=1)
    else:
        # For weekly view, just add one day
        next_date = max_date + pd.Timedelta(days=1)
        new_row = template_row.copy()
        new_row['Date'] = next_date
        new_rows.append(new_row)
    
    if new_rows:
        # Create DataFrame from new rows
        new_data = pd.DataFrame(new_rows)
        
        # Set numeric columns to zero
        numeric_columns = ['Sales Dollars', 'Units Sold']
        for col in numeric_columns:
            if col in new_data.columns:
                new_data[col] = 0
        
        # Append the new rows to the original data
        extended_data = pd.concat([data, new_data], ignore_index=True)
        return extended_data
    
    return data

def get_next_weekday(start_date, weekday):
    """
    Get the next occurrence of specified weekday (0=Monday, 6=Sunday).
    If start_date is already the specified weekday, return start_date.
    """
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return start_date + timedelta(days=days_ahead)

def get_month_end(year, month):
    """Calculate the last day of the given month."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return next_month - timedelta(days=1)

def get_month_start(date_obj):
    """Get the first day of the month for a given date."""
    return date(date_obj.year, date_obj.month, 1)

def get_month_bounds(date_obj):
    """Get the start and end dates for the month containing the given date."""
    start = get_month_start(date_obj)
    end = get_month_end(date_obj.year, date_obj.month)
    return start, end

def get_default_dates(valid_starts, valid_ends, min_date, max_date, view_type='Weekly'):
    """
    Get sensible default start and end dates based on the view type.
    For weekly view, defaults to the most recent complete week.
    For monthly view, defaults to the most recent complete month.
    """
    if not valid_starts or not valid_ends:
        return min_date, max_date
    
    if view_type == 'Monthly':
        # For monthly view, get the most recent complete month
        latest_date = max_date
        start_date, end_date = get_month_bounds(latest_date)
        
        # If we're in the middle of a month, use the previous month
        if latest_date.day < latest_date.replace(day=28).day:  # Not at month end
            previous_month = latest_date.replace(day=1) - timedelta(days=1)
            start_date, end_date = get_month_bounds(previous_month)
        
        return start_date, end_date
    else:
        # Weekly view logic remains the same
        valid_start = valid_starts[-1]
        valid_end = valid_ends[-1]
        for end in valid_ends:
            if end >= valid_start:
                valid_end = end
                break
                
        return valid_start, valid_end

def get_valid_dates(data, view_type='Weekly', start_on_monday=True):
    """
    Get valid start and end dates based on actual data points.
    Returns two lists of datetime.date objects representing valid start and end dates.
    """
    # Extend data with future records for proper date range selection
    extended_data = extend_data_with_future_record(data, view_type=view_type)
    
    dates = sorted(extended_data['Date'].dt.date.unique())
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
        
        # For the end dates, we want to find all Sundays (or Saturdays)
        # Including the next one after the last date if needed
        target_end_weekday = 6 if start_on_monday else 5  # Sunday or Saturday
        
        current_date = min_date
        last_date = max_date
        while current_date <= last_date:
            weekday = current_date.weekday()
            if weekday == target_end_weekday:
                valid_ends.append(current_date)
            current_date += timedelta(days=1)
        
        # If the last valid end isn't after the last date, add the next appropriate weekday
        if not valid_ends or valid_ends[-1] < last_date:
            next_end = get_next_weekday(last_date, target_end_weekday)
            valid_ends.append(next_end)
                    
    else:  # Monthly view
        valid_starts = []
        valid_ends = []
        
        # Get the first and last months in the data
        min_month_start = get_month_start(min_date)
        max_month_start = get_month_start(max_date)
        
        # Generate all month boundaries between min and max dates
        current_date = min_month_start
        while current_date <= max_month_start:
            valid_starts.append(current_date)
            month_end = get_month_end(current_date.year, current_date.month)
            valid_ends.append(month_end)
            
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
    
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
    
    # Extend data with future record for proper date range selection
    extended_data = extend_data_with_future_record(data)
    
    min_date = extended_data['Date'].min().date()
    max_date = extended_data['Date'].max().date()
    
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
    valid_starts, valid_ends = get_valid_dates(extended_data, view_type, start_on_monday)
    
    if not valid_starts or not valid_ends:
        st.error("No valid date ranges found in the data")
        return min_date, max_date
    
    # Get default dates
    default_start, default_end = get_default_dates(valid_starts, valid_ends, min_date, max_date, view_type)
    
    # Ensure default dates are within the valid range
    default_start = max(min(default_start, max_date), min_date)
    default_end = max(min(default_end, valid_ends[-1]), min_date)
    
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
        
        # Get valid end dates based on selected start date
        valid_end_dates = get_valid_end_dates(start_date, valid_ends)
        if not valid_end_dates:
            valid_end_dates = [max_date]
        
        # Ensure the default end date is within the valid range and is a proper week ending
        if view_type == 'Weekly':
            target_weekday = 6 if start_on_monday else 5  # Sunday or Saturday
            default_end = get_next_weekday(start_date, target_weekday)
        else:
            default_end = max(min(default_end, max_date), start_date)
        
        end_date = st.date_input(
            end_label,
            value=default_end,
            min_value=start_date,
            max_value=valid_ends[-1],
            key=f"{key_prefix}_end_date"
        )
        
        # If selected date isn't a valid end date, find the nearest one
        if end_date not in valid_end_dates:
            nearest_end = min(valid_end_dates, key=lambda x: abs((x - end_date).days))
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