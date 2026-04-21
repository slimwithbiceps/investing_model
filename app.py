import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. SETTINGS & LOAN CONSTANTS ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")

# Indian Bank Sanction Metrics
LOAN_APR = 0.0763  
TAX_RATE = 0.20
TAX_ADJUSTED_TARGET = LOAN_APR / (1 - TAX_RATE) # 9.54%
EMI_VAL = 40573
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 6667 

# Google Sheet Link (Ensure it is published as CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" 

# EXPANDED 100-STOCK UNIVERSE
UNIVERSE_100 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", 
    "ITC.NS", "HUL.NS", "LTIM.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS", "ADANIPORTS.NS", 
    "KOTAKBANK.NS", "TITAN.NS", "AXISBANK.NS", "ASIANPAINT.NS", "ULTRACEMCO.NS", "NTPC.NS", "TATAMOTORS.NS", 
    "M&M.NS", "ONGC.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "ADANIPOWER.NS", 
    "TRENT.NS", "HAL.NS", "BEL.NS", "ZOMATO.NS", "VBL.NS", "DLF.NS", "SIEMENS.NS", "GRASIM.NS", "HINDALCO.NS", 
    "NESTLEIND.NS", "SBILIFE.NS", "BAJAJ-AUTO.NS", "WIPRO.NS", "TECHM.NS", "EICHERMOT.NS", "INDUSINDBK.NS", 
    "DIVISLAB.NS", "BPCL.NS", "CIPLA.NS", "HCLTECH.NS", "GAIL.NS", "PNB.NS", "IRFC.NS", "RECLTD.NS", "PFC.NS",
    "IOC.NS", "TATAELXSI.NS", "POLYCAB.NS", "CANBK.NS", "CHOLAFIN.NS", "SHREECEM.NS", "BAJAJHLDNG.NS",
    "LODHA.NS", "TATACOMM.NS", "JINDALSTEL.NS", "AMBUJACEM.NS", "ABB.NS", "HAVELLS.NS", "PIDILITIND.NS",
    "TATACONSUM.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "GODREJCP.NS", "MAZDOCK.NS", "RVNL.NS", "IRCTC.NS", 
    "PAGEIND.NS", "TVSMOTOR.NS", "HEROMOTOCO.NS", "CUMMINSIND.NS", "MAXHEALTH.NS", "MANKIND.NS", "BOSCHLTD.NS", 
    "PERSISTENT.NS", "DIXON.NS", "OBEROIRLTY.NS", "TATACHEM.NS", "PETRONET.NS", "MRF.NS", "COLPAL.NS", 
    "JUBLFOOD.NS", "BHEL.NS", "NMDC.NS", "AUBANK.NS", "YESBANK.NS", "LT.NS", "BERGEPAINT.NS"
]

@st.cache_data(ttl=86400)
def fetch_all_data():
    nifty = yf.download("^NSEI", period="1y", interval="1d")['Close'].squeeze()
    stocks = yf.download(UNIVERSE_100, period="1y", interval="1d")['Close']
    return nifty, stocks

def run_analysis(nifty, stocks):
    # 14-Day Smoothing Filter
    m_6m = ((stocks / stocks.shift(126)) - 1).rolling(14).mean()
    vol = (stocks.pct_change().rolling(126).std() * np.sqrt(252)).rolling(14).mean()
    efficiency = (m_6m / vol).iloc[-1]
    n_ret = ((nifty.iloc[-1] / nifty.iloc[-126]) - 1)
    
    results = []
    for t in UNIVERSE_100:
        try:
            info = yf.Ticker(t).info
            results.append({
                "Ticker": t.replace(".NS",""), 
                "Sector": info.get('sector', 'Other'),
                "Verdict": "💎 ELITE" if (m_6m[t].iloc[-1] > n_ret and efficiency[t] > 0.8) else ("✅ STABLE" if efficiency[t] > 0.4 else "🛑 WEAK"),
                "Momentum (6M)": m_6m[t].iloc[-1], 
                "Efficiency": efficiency[t], 
                "PE": info.get('trailingPE', 0)
            })
        except: continue
    return pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)

# --- UI SECTION ---
st.title("🛡️ EMI-Shield: Master Alpha Cockpit")

with st.expander("📖 DETAILED STRATEGY & LOAN GOALS", expanded=True):
    st.markdown(f"""
    **Mission:** Offset the **{LOAN_APR*100:.2f}% Loan APR** after-tax.
    - **Loan Profile:** ₹20,20,000 sanctioned with an EMI of ₹{EMI_VAL:,.0f}.
    - **Tax-Adjusted Goal:** **{TAX_ADJUSTED_TARGET*100:.2f}%** (Covers loan + 20% STCG tax).
    - **Smoothing Filter:** Using a **14-day Moving Average** to eliminate daily trading noise.
    """)

# PERFORMANCE CHART
st.header("📈 Strategy Performance vs Tax-Adjusted Benchmark")
try:
    ledger = pd.read_csv(SHEET_URL)
    ledger['Date'] = pd.to_datetime(ledger['Date'])
    nifty, stocks = fetch_all_data()
    
    start_date = ledger['Date'].min()
    dates = nifty.loc[start_date:].index
    port_vals = []
    
    for d in dates:
        active = ledger[ledger['Date'] <= d]
        # Resilient ticker mapping for chart
        val = sum(active['Qty'] * stocks.loc[d, active['Ticker'].astype(str) + ".NS"])
        port_vals.append((val / active['Total_Value'].sum()) - 1)
        
    perf = pd.DataFrame({
        "Date": dates, 
        "Portfolio": port_vals, 
        "Nifty 50": (nifty.loc[start_date:] / nifty.loc[start_date]) - 1,
        "Tax-Adj Goal (9.54%)": (1 + TAX_ADJUSTED_TARGET)**((dates - start_date).days/365) - 1
    })
    fig = px.line(perf, x="Date", y=["Portfolio", "Nifty 50", "Tax-Adj Goal (9.54%)"])
    fig.update_traces(line=dict(dash='dash', color='red'), selector=dict(name="Tax-Adj Goal (9.54%)"))
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("💡 Chart requires 'Date' (YYYY-MM-DD) and 'Ticker' (e.g. TRENT) in Google Sheets.")

# AUDIT SECTION
st.divider()
st.header("♻️ Strategy Portfolio Audit (Recycle Engine)")
if st.button("🔍 AUDIT CURRENT HOLDINGS"):
    try:
        ledger = pd.read_csv(SHEET_URL)
        nifty, stocks = fetch_all_data()
        analysis = run_analysis(nifty, stocks)
        audit = ledger.merge(analysis, on="Ticker", how="left")
        audit['Action'] = audit['Verdict'].apply(lambda x: "🛑 RECYCLE (SELL)" if x == "🛑 WEAK" else "💎 HOLD")
        
        st.dataframe(audit[['Ticker', 'Action', 'Verdict', 'Momentum (6M)', 'Efficiency', 'PE']], use_container_width=True)
        to_sell = audit[audit['Action'] == "🛑 RECYCLE (SELL)"]
        if not to_sell.empty:
            st.error(f"Sell recommendations: {', '.join(to_sell['Ticker'].tolist())}")
    except: st.error("Audit failed. Check ticker names in your Sheet.")

# DEPLOYMENT SECTION
st.divider()
st.header(f"🎯 Deployment: Fresh ₹{FORTNIGHTLY_SIP}")
if st.button("🚀 RUN TOP 100 ALPHA SCAN"):
    nifty, stocks = fetch_all_data()
    df = run_analysis(nifty, stocks)
    df.index += 1 # Order serial numbers correctly
    
    elites = df[df['Verdict'] == "💎 ELITE"].head(3)
    cols = st.columns(3)
    for i, (idx, row) in enumerate(elites.iterrows()):
        cols[i].metric(row['Ticker'], f"₹{PER_STOCK_SIP}", f"Score: {row['Efficiency']:.2f}")
    
    st.dataframe(df, column_config={
        "Momentum (6M)": st.column_config.NumberColumn(format="%.1f%%"), 
        "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
        "PE": st.column_config.NumberColumn("PE Ratio")
    }, use_container_width=True)

# GLOSSARY
st.divider()
st.header("📚 The Investor's Dictionary")
g1, g2 = st.columns(2)
with g1:
    with st.expander("📈 XIRR (Extended Internal Rate of Return)", expanded=True):
        st.write("Your personal interest rate. Accounts for the specific timing of your fortnightly deposits.")
        st.latex(r"XIRR = \text{Internal Rate where NPV of Cashflows is Zero}")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("The stock's speed. We buy stocks outperforming the market average.")
with g2:
    with st.expander("🎯 Efficiency (Sharpe Ratio)", expanded=True):
        st.write("Measures 'Smoothness'. A score > 1.0 means the stock is climbing with very little volatility.")
        st.latex(r"Sharpe = \frac{R_p - R_f}{\sigma_p}")
    with st.expander("🛡️ 200-DMA"):
        st.write("The 200-day health line. If the market is below this, we stop buying to protect capital.")
