import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# --- CONFIG ---
st.set_page_config(page_title="EMI-Shield Cockpit", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" # Publish to Web > CSV

def get_market_data(tickers):
    data = yf.download(tickers, period="1y", interval="1wk")['Close']
    # Benchmarks
    returns = (data.iloc[-1] / data.iloc[-26]) - 1 # 6-month
    vol = data.pct_change().std() * np.sqrt(52)
    efficiency = returns / vol
    
    results = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            pe = info.get('trailingPE', 50)
            results.append({
                "Ticker": t,
                "Momentum": min(max(returns[t] * 2, 0), 1.0), # Normalized for bar
                "Efficiency": min(max(efficiency[t] / 2, 0), 1.0), # Normalized for bar
                "Valuation": pe,
                "CurrentPrice": data[t].iloc[-1]
            })
        except: continue
    return pd.DataFrame(results)

# --- THE COCKPIT ---
st.title("🛰️ EMI-Shield: Command Center")

# Load Portfolio Memory
try:
    my_stocks = pd.read_csv(SHEET_URL)
    portfolio_tickers = my_stocks['Ticker'].unique().tolist()
except:
    my_stocks = pd.DataFrame()
    portfolio_tickers = []

# Universe for new buys
universe = ["HAL.NS", "BEL.NS", "TRENT.NS", "ZOMATO.NS", "RELIANCE.NS", "TCS.NS", "ITC.NS", "BHARTIARTL.NS", "TATAMOTORS.NS", "COALINDIA.NS"]
all_data = get_market_data(list(set(universe + portfolio_tickers)))

# --- SECTION 1: NEW CAPITAL (THE ₹45K SIP) ---
st.header("1️⃣ New Capital Deployment (₹45,000)")
st.subheader("Target: Top 3 Stocks (₹15,000 each)")

top_10 = all_data[all_data['Ticker'].isin(universe)].sort_values("Efficiency", ascending=False).head(10).reset_index(drop=True)

st.dataframe(
    top_10,
    column_config={
        "Momentum": st.column_config.ProgressColumn("Speed vs Nifty", format=" ", min_value=0, max_value=1),
        "Efficiency": st.column_config.ProgressColumn("Ride Smoothness", format=" ", min_value=0, max_value=1),
        "Valuation": st.column_config.NumberColumn("Price Tag (P/E)", format="%d", help="Red is Expensive"),
    },
    hide_index=True,
    use_container_width=True
)

# --- SECTION 2: PORTFOLIO MONITOR ---
st.divider()
st.header("2️⃣ Existing Holdings Tracker")

if not my_stocks.empty:
    # Merge holdings with live data
    monitor = my_stocks.merge(all_data, on="Ticker")
    monitor['Returns'] = ((monitor['CurrentPrice'] - monitor['BuyPrice']) / monitor['BuyPrice']) * 100
    
    def get_action(row):
        if row['Efficiency'] < 0.2 or row['Valuation'] > 70: return "🛑 SELL"
        return "💎 HOLD"

    monitor['Action'] = monitor.apply(get_action, axis=1)
    
    # Display Table
    st.dataframe(
        monitor[['Ticker', 'Returns', 'Action', 'Efficiency', 'Valuation']],
        column_config={
            "Returns": st.column_config.NumberColumn("Total Return %", format="%.1f%%"),
            "Action": st.column_config.TextColumn("Verdict"),
            "Efficiency": st.column_config.ProgressColumn("Current Health", min_value=0, max_value=1),
        },
        use_container_width=True
    )
    
    # --- SECTION 3: THE RECYCLE PLAN ---
    st.divider()
    st.header("3️⃣ Cash Recycling Instructions")
    to_sell = monitor[monitor['Action'] == "🛑 SELL"]
    
    if not to_sell.empty:
        total_sell_value = (to_sell['Qty'] * to_sell['CurrentPrice']).sum()
        st.warning(f"⚠️ Action Required: Sell indicated stocks to free up ₹{total_sell_value:,.0f}")
        st.info(f"👉 **Re-invest that ₹{total_sell_value:,.0f}** equally into the Top 3 stocks from the 'New Capital' list above.")
    else:
        st.success("✅ No recycling needed today. Your existing holdings are healthy.")

else:
    st.info("Your portfolio is currently empty. Run your first ₹45k SIP using Section 1.")
