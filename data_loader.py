#data_loader.py
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import streamlit as st

# Define constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
REQUIRED_COLUMNS = ['Retailer', 'Product SKU', 'Product Title', 'Color', 'Size', 'Units Sold', 'Sales Dollars', 'Date']

def get_google_credentials():
    """Securely retrieve Google Sheets credentials."""
    try:
        return service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
    except Exception as e:
        st.error(f"⚠️ Credential Error: {str(e)}")
        st.info("Please ensure your Google service account credentials are properly configured in Streamlit secrets.")
        return None

@st.cache_data(ttl=3600)
def load_data_from_gsheet(spreadsheet_id, range_name):
    """
    Load and validate data from Google Sheets with proper error handling.
    Returns tuple: (DataFrame or None, error message or None)
    """
    if not spreadsheet_id:
        return None, "Please enter a Google Sheet ID"
        
    # Add debug information
    st.sidebar.markdown("### Debug Information")
    st.sidebar.markdown(f"📝 Sheet ID: `{spreadsheet_id}`")
    st.sidebar.markdown(f"📍 Range: `{range_name}`")
    
    try:
        credentials = get_google_credentials()
        if not credentials:
            return None, "Failed to load Google credentials"
            
        if hasattr(credentials, 'service_account_email'):
            st.sidebar.markdown(f"🔑 Service Account: `{credentials.service_account_email}`")
        
        service = build('sheets', 'v4', credentials=credentials)
        
        try:
            metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            st.sidebar.markdown("✅ Successfully accessed sheet metadata")
            st.sidebar.markdown(f"📊 Sheet Title: `{metadata.get('properties', {}).get('title', 'Unknown')}`")
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return None, f"""Sheet not found. Please verify:
1. Sheet ID: {spreadsheet_id} is correct
2. The sheet is shared with: {credentials.service_account_email}
3. The sharing settings allow the service account to view the sheet
4. You've clicked 'Done' in the sharing dialog
5. The sheet name '{range_name.split('!')[0]}' matches exactly (case-sensitive)"""
            elif "403" in error_msg:
                return None, "Access denied. Please check sharing permissions"
            else:
                return None, f"Error accessing sheet metadata: {error_msg}"

        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None, "No data found in the specified sheet range"
        
        df = pd.DataFrame(values[1:], columns=values[0])
        
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            return None, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Convert data types with error handling
        df['Sales Dollars'] = pd.to_numeric(df['Sales Dollars'], errors='coerce')
        df['Units Sold'] = pd.to_numeric(df['Units Sold'], errors='coerce')
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Check for data conversion errors
        if df['Sales Dollars'].isna().any():
            st.warning("Some sales values could not be converted to numbers")
        if df['Units Sold'].isna().any():
            st.warning("Some unit values could not be converted to numbers")
        if df['Date'].isna().any():
            st.warning("Some dates could not be parsed properly")
            
        return df, None
        
    except Exception as e:
        error_message = str(e)
        if "404" in error_message:
            return None, "Sheet not found. Please check the Sheet ID and sharing permissions."
        elif "403" in error_message:
            return None, "Access denied. Please ensure the sheet is shared with your service account."
        else:
            return None, f"Error loading data: {error_message}"

def filter_data(data, retailer_filter, product_filter, date_range):
    """Filter data based on user selections."""
    filtered_data = data.copy()
    if "All" not in retailer_filter:
        filtered_data = filtered_data[filtered_data['Retailer'].isin(retailer_filter)]
    if "All" not in product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(product_filter)]
    filtered_data = filtered_data[
        (filtered_data['Date'].dt.date >= date_range[0]) &
        (filtered_data['Date'].dt.date <= date_range[1])
    ]
    return filtered_data

def calculate_metrics(data):
    """Calculate key business metrics from the data."""
    metrics = {
        'total_sales': data['Sales Dollars'].sum(),
        'total_units': data['Units Sold'].sum(),
        'avg_order_value': data['Sales Dollars'].mean(),
        'unique_products': data['Product Title'].nunique(),
        'unique_retailers': data['Retailer'].nunique()
    }
    return metrics