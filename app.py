import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- SETTINGS ---
st.set_page_config(page_title="EMI-Shield Pro 2026", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" # Share > Publish to Web > CSV

# APRIL 2026 MARKET BENCHMARKS
NIFTY_PE_BENCH = 21.4
NIFTY_200_DMA = 25170

def get_market_health():
    nifty = yf.download("^NSEI", period="1y", interval="1d")
    current_price = nifty['Close'].iloc[-1]
    dma_200 = nifty['Close'].rolling(window=200).mean().iloc[-1]
    daily_chg = nifty['Close'].pct_change().iloc[-1]
    weekly_chg = (nifty['Close'].iloc[-1] / nifty['Close'].iloc[-5]) - 1
    status = "🟢 BULLISH" if current_price > dma_200 else "🔴 CAUTION (Market Below 200-DMA)"
    return status, daily_chg, weekly_chg, current_price

def get_stock_analysis(tickers):
    data = yf.download(tickers, period="1y", interval="1wk")['Close']
    returns_6m = (data.iloc[-1] / data.iloc[-26]) - 1
    vol = data.pct_change().std() * np.sqrt(52)
    daily_data = yf.download(tickers, period="5d", interval="1d")['Close']
    daily_chg = daily_data.pct_change().iloc[-1]
    
    results = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            pe = info.get('trailingPE', 0)
            score = returns_6m[t] / vol[t]
            
            # REASONING LOGIC
            if score > 1.0 and pe < 45: verdict, rec = "💎 ELITE", "High efficiency, fair price."
            elif score > 0.5: verdict, rec = "✅ STABLE", "Healthy momentum."
            elif pe > 60: verdict, rec = "⚠️ BUBBLE", "Valuation disconnected from trend."
            else: verdict, rec = "🛑 WEAK", "Underperforming volatility risk."

            results.append({
                "Ticker": t, "Verdict": verdict, "Daily %": daily_chg[t],
                "Momentum (6M)": returns_6m[t], "Efficiency": score,
                "PE": pe, "Detailed Instruction": rec
            })
        except: continue
    return pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)

# --- UI LAYOUT ---
st.title("🛰️ EMI-Shield: Executive Dashboard")

# 1. MARKET HEALTH & REASONING
health, d_chg, w_chg, n_price = get_market_health()
st.subheader("🌍 Market Health Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Market Status", health)
c2.metric("Nifty 50 Price", f"{n_price:,.0f}")
c3.metric("Daily Change", f"{d_chg*100:.2f}%")
c4.metric("Weekly Change", f"{w_chg*100:.2f}%")

with st.expander("📖 Metric Guide (How we decide)"):
    st.write("**Efficiency:** Measures 'Smoothness'. 0.0 to 2.0. We want > 0.8 for EMI safety.")
    st.write("**Momentum (6M):** Must be > Nifty's 6M growth to justify direct trading.")
    st.write("**Verdict:** 'Elite' stocks are your primary targets for the ₹45k SIP.")

# 2. SIP HISTORY (From Google Sheets)
st.divider()
st.subheader("📈 Portfolio History & Memory")
try:
    my_stocks = pd.read_csv(SHEET_URL)
    fig = px.pie(my_stocks, values='Total_Value', names='Ticker', hole=0.4, title="Current Capital Allocation")
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Log your trades in Google Sheets to see your live allocation pie chart here.")

# 3. THE COMMANDS (The 3-Step Action Plan)
st.divider()
st.header("🎯 This Fortnight's Mission Plan")

universe = ["HAL.NS", "TRENT.NS", "BEL.NS", "ZOMATO.NS", "RELIANCE.NS", "TCS.NS", "BHARTIARTL.NS", "COALINDIA.NS", "NTPC.NS", "TATAMOTORS.NS"]
analysis = get_stock_analysis(universe)

# ACTION 1: NEW CAPITAL
with st.container():
    st.subheader("Step 1: Deploy New ₹45,000")
    top_3 = analysis[analysis['Verdict'].isin(["💎 ELITE", "✅ STABLE"])].head(3)
    if not top_3.empty:
        for i, row in top_3.iterrows():
            st.success(f"**Invest ₹15,000 in {row['Ticker']}** ({row['Detailed Instruction']})")
    else:
        st.error("Market is overheated. Hold your ₹45k in a Liquid Fund this fortnight.")

# ACTION 2: PORTFOLIO AUDIT
st.subheader("Step 2: Existing Holdings Audit")
st.dataframe(
    analysis,
    column_config={
        "Daily %": st.column_config.NumberColumn(format="%.2f%%"),
        "Momentum (6M)": st.column_config.ProgressColumn(min_value=0, max_value=1),
        "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
        "PE": st.column_config.NumberColumn("P/E Ratio", help=f"Nifty Bench: {NIFTY_PE_BENCH}")
    },
    use_container_width=True
)

# ACTION 3: RECYCLE
st.subheader("Step 3: Sell & Recycle Instructions")
sells = analysis[analysis['Verdict'] == "🛑 WEAK"]
if not sells.empty:
    st.warning(f"Sell recommendations found for: {', '.join(sells['Ticker'].tolist())}")
    st.write("Move the proceeds equally into the Top 3 stocks listed in Step 1.")
else:
    st.success("Your current holdings are outperforming. No 'Sell' actions required.")
