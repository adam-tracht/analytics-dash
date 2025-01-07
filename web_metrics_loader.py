# web_metrics_loader.py

import pandas as pd
import numpy as np  # Added numpy import
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from data_loader import get_google_credentials

@st.cache_data(ttl=3600)
def load_web_metrics(spreadsheet_id):
    """
    Load web metrics data from the web_metrics sheet.
    Returns tuple: (DataFrame or None, error message or None)
    """
    try:
        credentials = get_google_credentials()
        if not credentials:
            return None, "Failed to load Google credentials"
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Try to load the web metrics data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='web_metrics!A:E'  # Columns A-E for our metrics
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return None, "No web metrics data found"
            
        # Create DataFrame with column headers
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Validate required columns
        required_columns = ['Week', 'Sessions', 'Transactions', 'Purchase revenue', 'Engaged sessions']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, f"Missing required columns in web metrics sheet: {', '.join(missing_columns)}"
        
        # Convert Week to datetime
        df['Week'] = pd.to_datetime(df['Week'])
        
        # Convert numeric columns
        numeric_columns = ['Sessions', 'Transactions', 'Purchase revenue', 'Engaged sessions']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col].str.replace('$', '').str.replace(',', ''), errors='coerce')
        
        # Calculate derived metrics
        df['Conversion Rate'] = (df['Transactions'] / df['Sessions'] * 100).round(2)
        df['Bounce Rate'] = ((df['Sessions'] - df['Engaged sessions']) / df['Sessions'] * 100).round(2)
        df['AOV'] = (df['Purchase revenue'] / df['Transactions']).round(2)
        
        # Handle any invalid calculations
        df = df.replace([np.inf, -np.inf], np.nan)
        
        return df, None
        
    except Exception as e:
        error_message = str(e)
        if "404" in error_message:
            return None, "Web metrics sheet not found. Please ensure 'web_metrics' sheet exists."
        else:
            return None, f"Error loading web metrics data: {error_message}"