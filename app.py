import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- 1. SETTINGS & LOAN CONSTANTS ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")

LOAN_APR = 0.0763  # 7.63% APR
TAX_ADJUSTED_TARGET = 0.0954 
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 6667 
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" 

# Sector Index Mapping for Benchmarking
SECTOR_INDEX_MAP = {
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Auto": "^CNXAUTO",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty Metal": "^CNXMETAL",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY"
}

# FULL 100-STOCK UNIVERSE
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
    indices = ["^NSEI"] + list(SECTOR_INDEX_MAP.values())
    all_data = yf.download(UNIVERSE_100 + indices, period="1y", interval="1d")['Close']
    return all_data

def run_analysis(data):
    # 14-Day Smoothing Filter
    stocks = data[UNIVERSE_100]
    nifty = data["^NSEI"]
    
    m_6m = ((stocks / stocks.shift(126)) - 1).rolling(14).mean()
    vol = (stocks.pct_change().rolling(126).std() * np.sqrt(252)).rolling(14).mean()
    efficiency = (m_6m / vol).iloc[-1]
    n_ret = ((nifty.iloc[-1] / nifty.iloc[-126]) - 1)
    
    fundamental_data = []
    for t in UNIVERSE_100:
        try:
            info = yf.Ticker(t).info
            fundamental_data.append({
                "Ticker": t.replace(".NS",""),
                "Industry": info.get('industry', 'Other'),
                "PE": info.get('trailingPE', 0),
                "Momentum": m_6m[t].iloc[-1],
                "Efficiency": efficiency[t]
            })
        except: continue
    
    df = pd.DataFrame(fundamental_data)
    industry_pe = df.groupby('Industry')['PE'].median().to_dict()
    df['Industry Median PE'] = df['Industry'].map(industry_pe)
    df['Verdict'] = df.apply(lambda r: "💎 ELITE" if (r['Momentum'] > n_ret and r['Efficiency'] > 0.8) else ("✅ STABLE" if r['Efficiency'] > 0.4 else "🛑 WEAK"), axis=1)
    return df.sort_values("Efficiency", ascending=False).reset_index(drop=True)

# --- UI SECTION ---
st.title("🛡️ EMI-Shield: Master Alpha Cockpit")

with st.expander("📖 DETAILED STRATEGY & LOAN GOALS", expanded=True):
    st.markdown(f"""
    **Mission:** Offset the **{LOAN_APR*100:.2f}% Loan APR** after-tax.
    - **Loan Profile:** ₹20,20,000 sanctioned | EMI: ₹40,573.
    - **Tax-Adjusted Goal:** **9.54%** (Covers interest + 20% STCG tax).
    - **Smoothing Filter:** Using 14-day Moving Averages to reduce daily noise.
    """)

# PERFORMANCE CHART
st.header("📈 Portfolio Returns vs Benchmark (%)")
selected_sector = st.selectbox("Switch Sector Benchmark:", list(SECTOR_INDEX_MAP.keys()))

try:
    ledger = pd.read_csv(SHEET_URL)
    ledger['Date'] = pd.to_datetime(ledger['Date'])
    all_data = fetch_all_data()
    
    start_date = ledger['Date'].min()
    dates = all_data.loc[start_date:].index
    port_returns = []
    
    for d in dates:
        active = ledger[ledger['Date'] <= d]
        if active.empty:
            port_returns.append(0)
            continue
        
        current_val = sum(active['Qty'] * all_data.loc[d, active['Ticker'] + ".NS"])
        total_invested = active['Total_Value'].sum()
        port_returns.append(((current_val / total_invested) - 1) * 100)
        
    perf = pd.DataFrame({
        "Date": dates, 
        "My Portfolio (%)": port_returns, 
        "Nifty 50 (%)": ((all_data.loc[start_date:, "^NSEI"] / all_data.loc[start_date, "^NSEI"]) - 1) * 100,
        f"{selected_sector} (%)": ((all_data.loc[start_date:, SECTOR_INDEX_MAP[selected_sector]] / all_data.loc[start_date, SECTOR_INDEX_MAP[selected_sector]]) - 1) * 100,
        "Tax-Adj Goal (9.54%)": (((1 + TAX_ADJUSTED_TARGET)**((dates - start_date).days/365)) - 1) * 100
    })
    
    fig = px.line(perf, x="Date", y=["My Portfolio (%)", "Nifty 50 (%)", f"{selected_sector} (%)", "Tax-Adj Goal (9.54%)"])
    fig.update_traces(line=dict(dash='dash', color='red'), selector=dict(name="Tax-Adj Goal (9.54%)"))
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("💡 Ensure Google Sheet data is correctly formatted with 'Date', 'Ticker', 'Qty', and 'Total_Value'.")

# AUDIT SECTION
st.divider()
st.header("♻️ Strategy Portfolio Audit (Recycle Engine)")
if st.button("🔍 AUDIT CURRENT HOLDINGS"):
    data = fetch_all_data()
    analysis = run_analysis(data)
    ledger = pd.read_csv(SHEET_URL)
    audit = ledger.merge(analysis, on="Ticker", how="left")
    audit['Action'] = audit['Verdict'].apply(lambda x: "🛑 RECYCLE (SELL)" if x == "🛑 WEAK" else "💎 HOLD")
    st.dataframe(audit[['Ticker', 'Action', 'Verdict', 'Momentum', 'Efficiency', 'PE']], use_container_width=True)

# DEPLOYMENT SECTION
st.divider()
st.header(f"🎯 Deployment: Fresh ₹{FORTNIGHTLY_SIP}")
if st.button("🚀 RUN TOP 100 ALPHA SCAN"):
    data = fetch_all_data()
    df = run_analysis(data)
    df.index += 1
    
    elites = df[df['Verdict'] == "💎 ELITE"].head(3)
    cols = st.columns(3)
    for i, (idx, row) in enumerate(elites.iterrows()):
        cols[i].metric(row['Ticker'], f"₹{PER_STOCK_SIP}", f"Eff: {row['Efficiency']:.2f}")
    
    st.dataframe(df, column_config={
        "Momentum": st.column_config.NumberColumn(format="%.1f%%"), 
        "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
        "PE": st.column_config.NumberColumn("Stock PE"),
        "Industry Median PE": st.column_config.NumberColumn("Ind. Median")
    }, use_container_width=True)

# GLOSSARY
st.divider()
st.header("📚 The Investor's Dictionary")
c1, c2 = st.columns(2)
with c1:
    with st.expander("📈 XIRR (Extended Internal Rate of Return)", expanded=True):
        st.write("Your personal interest rate. It accounts for the timing of your fortnightly deposits.")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("The speed of a stock. If the market grows 2% and your stock grows 5%, your Alpha is 3%.")
with c2:
    with st.expander("🎯 Efficiency (Sharpe Ratio)", expanded=True):
        st.write("Measures 'Smoothness'. A score > 1.0 means the stock is climbing with low volatility.")
    with st.expander("🛡️ 200-DMA"):
        st.write("The 200-day health line. If Nifty is below this, we stop buying to protect capital.")
