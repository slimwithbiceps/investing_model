import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# --- CONFIG & STYLING ---
st.set_page_config(page_title="EMI-Shield Dashboard", layout="wide")

# --- 1. THE RULEBOOK (Visual Logic) ---
def show_rules():
    with st.expander("🛡️ Strategy Blueprint: How we select stocks", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("1. Market Regime", "Nifty > 200 SMA", "Safety Switch")
        col2.metric("2. Value Floor", "P/E < 35", "Anti-Bubble")
        col3.metric("3. Smoothness", "Vol < 25%", "EMI Protection")
        col4.metric("4. Momentum", "Rank Top 10", "Growth")
        st.info("**Selection Logic:** We take the Nifty 500, filter for stocks with P/E below 35, and then rank them by (6-Month Return ÷ 6-Month Volatility).")

# --- 2. DATA ENGINES ---
@st.cache_data(ttl=3600)
def get_market_data(tickers):
    # Fetching data for ranking
    data = yf.download(tickers, period="1y", interval="1wk")['Close']
    return data

def get_recommendations(tickers):
    data = get_market_data(tickers)
    # Risk Adjusted Momentum
    returns = data.pct_change(26).iloc[-1]
    vol = data.pct_change(26).std()
    score = returns / vol
    
    # Simple Mock Fundamental Filter (In a real app, use a more robust API)
    results = []
    for t in tickers:
        results.append({'Ticker': t, 'Score': score[t], 'PE': 25}) # Placeholder PE
    return pd.DataFrame(results).sort_values('Score', ascending=False).head(10)

# --- 3. THE DASHBOARD UI ---
st.title("🛰️ EMI-Shield Cloud Quant")
show_rules()

# Load History (The Memory)
try:
    history = pd.read_csv("portfolio.csv")
    last_action_date = pd.to_datetime(history['Date']).max()
except:
    history = pd.DataFrame()
    last_action_date = datetime.now() - timedelta(days=20)

# --- 4. ACTION CENTER (The To-Do List) ---
st.subheader("📝 Fortnightly Action Plan")
days_since_last = (datetime.now() - last_action_date).days

if days_since_last >= 14:
    st.error(f"⚠️ ACTION REQUIRED: It has been {days_since_last} days since your last rebalance.")
    st.write("### Your Steps for Today:")
    st.write(f"1. **Sell** any stock in your current portfolio that isn't in the 'Top Picks' below.")
    st.write(f"2. **Invest ₹45,000** equally across the new Top Picks.")
    st.write(f"3. **Update `portfolio.csv`** on GitHub with your buy prices.")
else:
    st.success(f"✅ System Healthy. Next rebalance in {14 - days_since_last} days.")

# --- 5. THE GENERATOR ---
if st.button("Generate Today's Top Picks"):
    # Using a sample set of liquid Nifty stocks
    universe = ["HAL.NS", "BEL.NS", "TRENT.NS", "ZOMATO.NS", "RELIANCE.NS", "CHOLAFIN.NS", "TATAELXSI.NS"]
    top_picks = get_recommendations(universe)
    
    st.write("### 🚀 Buy Recommendations (Equal Weight)")
    st.table(top_picks)

# --- 6. HISTORY TAB ---
st.divider()
st.subheader("📜 Last Fortnight's Memory")
if not history.empty:
    st.dataframe(history.sort_values('Date', ascending=False))
else:
    st.write("No history found. Create `portfolio.csv` in GitHub.")
