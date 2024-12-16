# inventory_loader.py
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import streamlit as st
from data_loader import get_google_credentials

def parse_date(date_str):
    """Helper function to parse dates in various formats."""
    try:
        # Try common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except ValueError:
                continue
        # If none of the explicit formats work, let pandas try to parse it
        return pd.to_datetime(date_str)
    except:
        return None

@st.cache_data(ttl=3600)
def load_inventory_data(spreadsheet_id):
    """
    Load inventory data from the inventory_data sheet.
    Returns tuple: (DataFrame or None, error message or None)
    """
    try:
        credentials = get_google_credentials()
        if not credentials:
            return None, "Failed to load Google credentials"
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Try to load the inventory data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='inventory_data!A:H'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None, "No inventory data found"
            
        # Create DataFrame with column headers
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Validate required columns
        required_columns = ['Date', 'SKU', 'Category', 'Product Title', 'Color', 'Size', 'OH Qty']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"Missing required columns in inventory sheet: {', '.join(missing_columns)}"
        
        # Convert Date to datetime
        df['Date'] = pd.to_datetime(df['Date'].apply(parse_date))
        invalid_dates = df[df['Date'].isna()]
        if not invalid_dates.empty:
            st.warning(f"Found {len(invalid_dates)} rows with invalid dates. These rows will be excluded.")
            df = df.dropna(subset=['Date'])
        
        # Convert OH Qty to numeric, handling commas in numbers
        df['OH Qty'] = df['OH Qty'].astype(str).str.replace(',', '').astype(float)
        
        # Clean dimension values
        for dimension in ['Color', 'Size']:
            df[dimension] = df[dimension].fillna('N/A')
            df[dimension] = df[dimension].replace(['', ' ', '0', '0.0'], 'N/A')
        
        return df, None
        
    except Exception as e:
        error_message = str(e)
        if "404" in error_message:
            return None, "Inventory sheet not found. Please ensure 'inventory_data' sheet exists."
        else:
            return None, f"Error loading inventory data: {error_message}"