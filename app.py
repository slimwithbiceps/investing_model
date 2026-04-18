import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime

# --- CONFIG ---
# Replace this with your Google Sheet "Export as CSV" link
# To get this: File > Share > Publish to Web > Link > Entire Document > CSV
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" 

st.set_page_config(page_title="EMI-Shield: Command Center", layout="wide")

def get_rankings(tickers):
    # Fetch Data
    data = yf.download(tickers, period="1y", interval="1wk")['Close']
    
    # Calculate Components
    returns_26w = (data.iloc[-1] / data.iloc[-26]) - 1
    volatility = data.pct_change().std() * np.sqrt(52)
    ra_score = returns_26w / volatility
    
    # Build Table
    results = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            pe = info.get('trailingPE', 0)
            results.append({
                'Ticker': t,
                'Momentum (26w)': f"{returns_26w[t]*100:.1f}%",
                'Volatility': f"{volatility[t]*100:.1f}%",
                'Efficiency Score': round(ra_score[t], 2),
                'P/E Ratio': pe,
                'Status': "PASS" if pe < 35 and ra_score[t] > 0.5 else "FAIL"
            })
        except: continue
    return pd.DataFrame(results).sort_values('Efficiency Score', ascending=False)

# --- DASHBOARD UI ---
st.title("🛡️ EMI-Shield Command Center")

# 1. ACTION LOGIC
st.sidebar.header("Daily Mission Control")
last_rebalance = datetime(2024, 4, 15) # This should ideally come from your Sheet
days_passed = (datetime.now() - last_rebalance).days

with st.expander("🚨 TODAY'S EXACT STEPS", expanded=True):
    if days_passed >= 14:
        st.error("❗ REBALANCE DUE TODAY")
        st.write("1. Open Zerodha/Groww.")
        st.write("2. Sell any holding marked 'FAIL' in the table below.")
        st.write("3. Buy the Top 3 NEW 'PASS' stocks (₹15,000 each).")
        st.write("4. Update your Google Sheet 'Trades' tab.")
    else:
        st.success(f"✅ HOLD POSITIONS. Next rebalance in {14 - days_passed} days.")
        st.info("Check individual 'Status' below. If a stock you own is 'FAIL', consider an early exit.")

# 2. THE QUANT MODEL
if st.button("Run Market Scan"):
    universe = ["HAL.NS", "BEL.NS", "TRENT.NS", "RELIANCE.NS", "ITC.NS", "ADANIPORTS.NS", "TCS.NS"]
    ranks = get_rankings(universe)
    
    st.subheader("📊 Market Analysis & Benchmarks")
    st.dataframe(ranks.style.applymap(lambda x: 'color: green' if x == 'PASS' else 'color: red', subset=['Status']))

# 3. GOOGLE SHEETS INTEGRATION (VIEWER)
st.divider()
st.subheader("📑 Your Ledger (from Google Sheets)")
try:
    ledger = pd.read_csv(SHEET_CSV_URL)
    st.dataframe(ledger)
except:
    st.warning("Connect your Google Sheet CSV link in the code to see live trades here.")
