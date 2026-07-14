import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from engine.data_fetcher import BinanceDataFetcher
from engine.backtester import OrderFlowBacktester
from engine.order_flow import OrderFlowCalculator

# Page Config with dark theme vibe
st.set_page_config(
    page_title="Trader Dale - Order Flow Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling rules
st.markdown("""
<style>
    .stApp {
        background-color: #0d0f12;
        color: #e5e9f0;
    }
    div[data-testid="stSidebar"] {
        background-color: #16191f;
    }
    h1, h2, h3 {
        color: #4ec9b0 !important;
        font-family: 'Outfit', sans-serif;
    }
    .metric-card {
        background-color: #1b1f27;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4ec9b0;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Trader Dale Order Flow Dashboard")
st.markdown("Professional-grade order flow analytics, backtesting, and setup diagnostics.")

# Sidebar Configuration
st.sidebar.header("⚙️ Strategy Configuration")
symbol = st.sidebar.selectbox("Symbol", ["XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"], index=0)
timeframe = st.sidebar.selectbox("Interval", ["5m", "15m", "1h", "4h"], index=1)
limit = st.sidebar.slider("Candles Limit", 50, 500, 150)
imbalance_ratio = st.sidebar.slider("Imbalance Ratio", 1.5, 4.0, 2.5, step=0.1)

# Fetch Data
fetcher = BinanceDataFetcher(symbol=symbol)

with st.spinner("📥 Fetching historical data from Binance..."):
    try:
        klines = fetcher.fetch_klines(interval=timeframe, limit=limit)
        
        # Calculate Footprint VAH/VAL/POC for visual chart
        calculator = OrderFlowCalculator(imbalance_ratio=imbalance_ratio)
        poc, vah, val = calculator.calculate_volume_profile(klines)
        
        # Main Metrics row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>POC (Point of Control)</h3><h2>${poc:.4f}</h2></div>", unsafe_allowed_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>Value Area High</h3><h2>${vah:.4f}</h2></div>", unsafe_allowed_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h3>Value Area Low</h3><h2>${val:.4f}</h2></div>", unsafe_allowed_html=True)

        # Plot candlestick chart with VAH, VAL, POC overlay
        st.subheader(f"📈 {symbol} Candlestick & Volume Profile Overlay")
        
        fig = go.Figure(data=[go.Candlestick(
            x=klines['timestamp'],
            open=klines['open'],
            high=klines['high'],
            low=klines['low'],
            close=klines['close'],
            name="Price"
        )])
        
        # Add Value Area High, Low lines
        fig.add_hline(y=vah, line_dash="dash", line_color="#ff5555", annotation_text="Value Area High (VAH)")
        fig.add_hline(y=val, line_dash="dash", line_color="#50fa7b", annotation_text="Value Area Low (VAL)")
        fig.add_hline(y=poc, line_color="#f1fa8c", annotation_text="POC")
        
        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=500,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Run Backtest button
        st.subheader("🎯 Backtest Execution")
        if st.button("🚀 Run Backtest"):
            backtester = OrderFlowBacktester()
            results = backtester.run(klines)
            
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            with b_col1:
                st.metric("Net Profit", f"${results['net_profit']:.2f}")
            with b_col2:
                st.metric("Win Rate", f"{results['win_rate']:.2f}%")
            with b_col3:
                st.metric("Total Trades", results['total_trades'])
            with b_col4:
                st.metric("Profit Factor", f"{results['profit_factor']:.2f}")
                
            # Log of trades
            if results["trades"]:
                st.dataframe(pd.DataFrame(results["trades"]))
            else:
                st.info("No trades were triggered in this period.")

    except Exception as e:
        st.error(f"Failed to fetch data or run dashboard: {e}")
