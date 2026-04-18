import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- SETTINGS ---
st.set_page_config(page_title="EMI-Shield Pro 2026", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" # Share > Publish to Web > CSV

import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px

# --- CONFIG & BENCHMARKS ---
st.set_page_config(page_title="EMI-Shield Pro", layout="wide")
NIFTY_PE_BENCH = 21.38 # April 2026 Median
SHEET_URL = "YOUR_GOOGLE_SHEET_CSV_LINK" 

# EXTENDED 50-STOCK UNIVERSE
UNIVERSE_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS", "SBI.NS", "LICI.NS", 
    "ITC.NS", "HUL.NS", "LTIM.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS", "ADANIPORTS.NS", 
    "KOTAKBANK.NS", "TITAN.NS", "AXISBANK.NS", "ASIANPAINT.NS", "ULTRACEMCO.NS", "NTPC.NS", "TATAMOTORS.NS", 
    "M&M.NS", "ONGC.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "ADANIPOWER.NS", 
    "TRENT.NS", "HAL.NS", "BEL.NS", "ZOMATO.NS", "VBL.NS", "DLF.NS", "SIEMENS.NS", "GRASIM.NS", "HINDALCO.NS", 
    "NESTLEIND.NS", "SBILIFE.NS", "BAJAJ-AUTO.NS", "WIPRO.NS", "TECHM.NS", "EICHERMOT.NS", "INDUSINDBK.NS", 
    "DIVISLAB.NS", "BPCL.NS", "CIPLA.NS", "HCLTECH.NS"
]

def get_market_health():
    nifty = yf.download("^NSEI", period="1y", interval="1d")['Close'].squeeze()
    current_price = float(nifty.iloc[-1])
    dma_200 = float(nifty.rolling(window=200).mean().iloc[-1])
    status = "🟢 BULLISH" if current_price > dma_200 else "🟡 CAUTION (Below 200-DMA)"
    return status, current_price, dma_200

def run_analysis(tickers):
    data = yf.download(tickers, period="1y", interval="1wk")['Close']
    returns_6m = (data.iloc[-1] / data.iloc[-26]) - 1
    vol = data.pct_change().std() * np.sqrt(52)
    daily_chg = yf.download(tickers, period="2d", interval="1d")['Close'].pct_change().iloc[-1]
    
    results = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            pe = info.get('trailingPE', 0)
            score = returns_6m[t] / vol[t]
            
            if score > 0.8 and pe < 50: verdict = "💎 ELITE"
            elif score > 0.4: verdict = "✅ STABLE"
            else: verdict = "🛑 WEAK"

            results.append({
                "Ticker": t.replace(".NS", ""), 
                "Verdict": verdict,
                "Daily %": daily_chg[t] * 100,
                "Momentum (6M)": returns_6m[t],
                "Efficiency": score,
                "PE": pe
            })
        except: continue
    
    df = pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)
    df.index = df.index + 1 # Start serial number at 1
    return df

# --- DASHBOARD UI ---
st.title("🛡️ EMI-Shield Executive Cockpit")

# STRATEGY BOX
with st.expander("📖 VIEW DETAILED STRATEGY", expanded=True):
    st.markdown("""
    **Mission:** Generate **12% XIRR** to offset the **7.65% Car Loan** while managing a **₹25,000 fortnightly SIP**.
    *   **Selection:** We filter 50 Large-Cap stocks for *Efficiency* (Return/Risk).
    *   **Buy Rule:** Invest ₹8,333 each in the Top 3 'ELITE' stocks every fortnight.
    *   **Recycle Rule:** Sell any holding that drops to 'WEAK' and move proceeds to the current Top 1.
    """)

# MARKET HEALTH
status, price, dma = get_market_health()
c1, c2, c3 = st.columns(3)
c1.metric("Market Status", status)
c2.metric("Nifty 50", f"{price:,.0f}")
c3.metric("200-DMA Benchmark", f"{dma:,.0f}")

# ANALYSIS
if st.button("🚀 RUN FULL 50-STOCK SCAN"):
    analysis = run_analysis(UNIVERSE_50)
    
    # STEP 1: NEW CAPITAL
    st.header("1️⃣ Deployment: Fresh ₹25,000")
    buys = analysis[analysis['Verdict'] == "💎 ELITE"].head(3)
    if not buys.empty:
        for i, row in buys.iterrows():
            st.success(f"**Action:** Invest **₹8,333** in **{row['Ticker']}** (Efficiency: {row['Efficiency']:.2f})")
    else:
        st.warning("No ELITE stocks found. Consider parking ₹25k in a Liquid Fund.")

    # STEP 2: FULL DATA TABLE
    st.header("2️⃣ Global Market Scan (Ranked)")
    st.dataframe(
        analysis,
        column_config={
            "Daily %": st.column_config.NumberColumn(format="%.2f%%"),
            "Momentum (6M)": st.column_config.ProgressColumn(min_value=-0.2, max_value=1.0),
            "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
            "PE": st.column_config.NumberColumn("P/E Ratio")
        },
        use_container_width=True
    )

# SECTION 3: SIP MEMORY (PLACEHOLDER FOR GOOGLE SHEETS)
st.divider()
st.subheader("📑 SIP History & P&L Tracker")
try:
    ledger = pd.read_csv(SHEET_URL)
    st.write("Current Holdings and Live P&L will appear here once you connect the sheet.")
except:
    st.info("💡 Connect your Google Sheet CSV to see your live P&L and 'Hold/Sell' instructions.")
