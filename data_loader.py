# data_loader.py
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import streamlit as st
import numpy as np

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

# Define constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
REQUIRED_COLUMNS = [
    'Retailer', 
    'Product SKU', 
    'Product Title', 
    'Color', 
    'Size', 
    'Units Sold', 
    'Sales Dollars', 
    'Date',
    'Category'  # Category is now a required column
]

def get_google_credentials():
    """Securely retrieve Google Sheets credentials from Streamlit secrets or environment variables."""
    import os
    import json
    
    try:
        # First try to get credentials from Streamlit secrets
        try:
            return service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
        except Exception:
            # If Streamlit secrets fails, try environment variables
            if 'GOOGLE_CREDENTIALS' in os.environ:
                credentials_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
                return service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=SCOPES
                )
            else:
                raise Exception("No secrets found. Valid paths for a secrets.toml file or GOOGLE_CREDENTIALS environment variable required.")
    except Exception as e:
        st.error(f"⚠️ Credential Error: {str(e)}")
        st.info("Please ensure your Google service account credentials are properly configured in Streamlit secrets or as GOOGLE_CREDENTIALS environment variable.")
        return None

@st.cache_data(ttl=3600)
def load_context_data(spreadsheet_id, sheet_name='data_context'):
    """
    Load context information from a separate sheet in the spreadsheet.
    Returns tuple: (DataFrame or None, error message or None)
    """
    try:
        credentials = get_google_credentials()
        if not credentials:
            return None, "Failed to load Google credentials"
            
        service = build('sheets', 'v4', credentials=credentials)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='data_context!A:C'  # Explicitly specify the range
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None, "No context data found"
        
        # Create DataFrame with column headers
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Validate required columns
        required_columns = ['Category', 'Description', 'Notes']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"Missing required columns in context sheet: {', '.join(missing_columns)}"
            
        return df, None
        
    except Exception as e:
        error_message = str(e)
        if "404" in error_message:
            return None, "Context sheet not found. Please ensure 'data_context' sheet exists."
        else:
            return None, f"Error loading context data: {error_message}"

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
        
        # Create DataFrame with proper column headers
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Validate required columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            return None, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Clean and convert Sales Dollars with proper error handling
        try:
            # Remove currency symbols, commas, and whitespace from Sales Dollars
            df['Sales Dollars'] = (df['Sales Dollars']
                                 .str.replace('$', '', regex=False)
                                 .str.replace(',', '', regex=False)
                                 .str.strip())
            
            # Convert to numeric, coercing errors to NaN
            df['Sales Dollars'] = pd.to_numeric(df['Sales Dollars'], errors='coerce')
            
            # Log any rows where conversion failed
            invalid_sales = df[df['Sales Dollars'].isna()]
            if not invalid_sales.empty:
                st.warning(f"Found {len(invalid_sales)} rows with invalid sales values. These will be treated as $0.")
            
            # Replace NaN values with 0
            df['Sales Dollars'] = df['Sales Dollars'].fillna(0)
            
        except Exception as e:
            return None, f"Error converting Sales Dollars: {str(e)}"
        
        # Convert Units Sold to numeric
        try:
            df['Units Sold'] = pd.to_numeric(df['Units Sold'], errors='coerce')
            invalid_units = df[df['Units Sold'].isna()]
            if not invalid_units.empty:
                st.warning(f"Found {len(invalid_units)} rows with invalid unit values. These will be treated as 0.")
            df['Units Sold'] = df['Units Sold'].fillna(0).astype(int)
        except Exception as e:
            return None, f"Error converting Units Sold: {str(e)}"
        
        # Convert Date column
        try:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            invalid_dates = df[df['Date'].isna()]
            if not invalid_dates.empty:
                st.warning(f"Found {len(invalid_dates)} rows with invalid dates. These rows will be excluded.")
                df = df.dropna(subset=['Date'])
        except Exception as e:
            return None, f"Error converting dates: {str(e)}"
        
        # Clean Category values
        df['Category'] = df['Category'].fillna('Uncategorized')
        df['Category'] = df['Category'].replace(['', ' ', '0', '0.0'], 'Uncategorized')
        df['Category'] = df['Category'].astype(str).str.strip()
        
        # Validate final data
        if df.empty:
            return None, "No valid data rows found after cleaning"
        
        # Add Category statistics to sidebar
        st.sidebar.markdown("### Category Statistics")
        st.sidebar.markdown(f"📊 Total Categories: {df['Category'].nunique()}")
        st.sidebar.markdown("Top Categories:")
        category_counts = df.groupby('Category')['Units Sold'].sum().sort_values(ascending=False).head(3)
        for cat, count in category_counts.items():
            st.sidebar.markdown(f"- {cat}: {int(count):,} units")
        
        # Add general data quality metrics to sidebar
        st.sidebar.markdown("### Data Quality Metrics")
        st.sidebar.markdown(f"📊 Total Rows: {len(df)}")
        st.sidebar.markdown(f"📅 Date Range: {df['Date'].min().date()} to {df['Date'].max().date()}")
        st.sidebar.markdown(f"💰 Total Revenue: ${df['Sales Dollars'].sum():,.2f}")
        st.sidebar.markdown(f"📦 Total Units: {int(df['Units Sold'].sum()):,}")
        
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
    """
    Filter data based on user selections with proper type handling.
    """
    filtered_data = data.copy()
    
    # Apply retailer filter
    if "All" not in retailer_filter:
        filtered_data = filtered_data[filtered_data['Retailer'].isin(retailer_filter)]
    
    # Apply product filter
    if "All" not in product_filter:
        filtered_data = filtered_data[filtered_data['Product Title'].isin(product_filter)]
    
    # Apply date filter
    if date_range:
        filtered_data = filtered_data[
            (filtered_data['Date'].dt.date >= date_range[0]) &
            (filtered_data['Date'].dt.date <= date_range[1])
        ]
    
    return filtered_data

def calculate_metrics(data):
    """Calculate key business metrics from the data."""
    metrics = {
        'total_sales': data['Sales Dollars'].sum(),
        'total_units': int(data['Units Sold'].sum()),
        'avg_order_value': (data['Sales Dollars'].sum() / len(data)) if len(data) > 0 else 0,
        'unique_products': data['Product Title'].nunique(),
        'unique_retailers': data['Retailer'].nunique()
    }
    
    return metrics

@st.cache_data(ttl=3600)
def load_returns_data(spreadsheet_id):
    """Load returns data from the returns sheet."""
    try:
        credentials = get_google_credentials()
        if not credentials:
            return None, "Failed to load Google credentials"
            
        service = build('sheets', 'v4', credentials=credentials)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='returns!A:J'  # Adjust range to match your returns sheet
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None, "No returns data found"
        
        # Create DataFrame with column headers
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Validate required columns
        required_columns = ['Week', 'SKU', 'Total sales', 'Returns ($)', 
                          'Quantity returned', 'Orders', 'Quantity ordered',
                          'Product Title', 'Color', 'Size']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"Missing required columns in returns sheet: {', '.join(missing_columns)}"
        
        # Convert numeric columns
        numeric_columns = ['Total sales', 'Returns ($)', 'Quantity returned', 
                         'Orders', 'Quantity ordered']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col].str.replace('$', '', regex=False)
                                          .str.replace(',', '', regex=False)
                                          .str.strip(), 
                                  errors='coerce')
            
        # Convert Week to datetime
        df['Week'] = pd.to_datetime(df['Week'], errors='coerce')
        df = df.dropna(subset=['Week'])
        
        # Calculate return rate metrics
        df['Return Rate %'] = (df['Quantity returned'] / df['Quantity ordered'] * 100).round(2)
        df['Return Value Rate %'] = (df['Returns ($)'] / df['Total sales'] * 100).round(2)
        
        return df, None
        
    except Exception as e:
        error_message = str(e)
        if "404" in error_message:
            return None, "Returns sheet not found. Please ensure 'returns' sheet exists."
        else:
            return None, f"Error loading returns data: {error_message}"

@st.cache_data(ttl=3600)
def load_monthly_data(spreadsheet_id, range_name='monthly_sales'):
        """Load monthly sales data from the monthly_sales sheet."""
        try:
            credentials = get_google_credentials()
            if not credentials:
                return None, "Failed to load Google credentials"
                
            service = build('sheets', 'v4', credentials=credentials)
            
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f'{range_name}!A:I'  # Updated to include Category column
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None, "No monthly data found"
            
            # Create DataFrame with proper column headers
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # Clean Sales Dollars
            df['Sales Dollars'] = (df['Sales Dollars']
                                .str.replace('$', '', regex=False)
                                .str.replace(',', '', regex=False)
                                .str.strip())
            df['Sales Dollars'] = pd.to_numeric(df['Sales Dollars'], errors='coerce').fillna(0)
            
            # Clean Units Sold
            df['Units Sold'] = pd.to_numeric(df['Units Sold'], errors='coerce').fillna(0).astype(int)
            
            # Convert Date column
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            # Clean Category values
            if 'Category' in df.columns:
                df['Category'] = df['Category'].fillna('Uncategorized')
                df['Category'] = df['Category'].replace(['', ' ', '0', '0.0'], 'Uncategorized')
                df['Category'] = df['Category'].astype(str).str.strip()
            
            # Add category statistics to sidebar for monthly data
            if 'Category' in df.columns:
                st.sidebar.markdown("### Monthly Category Statistics")
                st.sidebar.markdown(f"📊 Total Categories: {df['Category'].nunique()}")
                st.sidebar.markdown("Top Categories (Monthly):")
                category_counts = df.groupby('Category')['Units Sold'].sum().sort_values(ascending=False).head(3)
                for cat, count in category_counts.items():
                    st.sidebar.markdown(f"- {cat}: {int(count):,} units")
            
            return df, None
            
        except Exception as e:
            error_message = str(e)
            if "404" in error_message:
                return None, "Monthly sales sheet not found. Please ensure 'monthly_sales' sheet exists."
            else:
                return None, f"Error loading monthly data: {error_message}"