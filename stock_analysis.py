import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
import base64
from io import BytesIO

def get_stock_data(stock_symbol):
    """
    Fetch historical stock data using Yahoo Finance API.
    Returns a DataFrame with stock price data.
    """
    try:
        stock = yf.Ticker(stock_symbol)
        df = stock.history(period="6mo")
        
        if df.empty:
            raise ValueError(f"⚠️ No data found for {stock_symbol}. Check the stock symbol.")
        
        return df

    except Exception as e:
        print(f"❌ Error fetching stock data: {e}")
        return pd.DataFrame()

def train_model(df):
    """
    Train a linear regression model on the stock price data.
    Predicts stock prices for the next 5 days.
    """
    try:
        if df.empty:
            raise ValueError("⚠️ Cannot train model: No data available.")

        if df['Close'].isnull().any():
            raise ValueError("⚠️ Close column contains NaN values. Cannot train model.")
        
        df = df.reset_index()
        df['Days'] = np.arange(len(df)).reshape(-1, 1)
        
        X = df[['Days']]
        y = df['Close']
        
        model = LinearRegression()
        model.fit(X, y)
        
        future_days = np.array([[len(df) + i] for i in range(1, 6)])  # Next 5 days
        predictions = model.predict(future_days)
        
        return predictions

    except Exception as e:
        print(f"❌ Error in training model: {e}")
        return []

def plot_stock(df):
    """
    Generates a stock price trend chart using Plotly and encodes it in Base64 format.
    """
    try:
        if df.empty:
            raise ValueError("⚠️ No data available for plotting.")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Stock Price'))
        fig.update_layout(title="Stock Price Trend", xaxis_title="Date", yaxis_title="Price", template="plotly_dark")

        # Convert Plotly figure to an image in Base64 format
        img_bytes = fig.to_image(format="png")
        img_base64 = base64.b64encode(img_bytes).decode()
        
        return img_base64

    except Exception as e:
        print(f"❌ Error in plotting stock data: {e}")
        return None
