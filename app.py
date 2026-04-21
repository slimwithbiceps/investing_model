import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. SETTINGS & DYNAMIC CONFIG ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")

# LOAN CONSTANTS (From Indian Bank Sanction April 2026)
LOAN_APR = 0.0763  # 7.63% APR
TAX_RATE = 0.20
TAX_ADJUSTED_BENCHMARK = LOAN_APR / (1 - TAX_RATE) # 9.54%
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 6667 

# Replace this with your Google Sheet "Published CSV" link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv"

# EXPANDED 100-STOCK UNIVERSE (Nifty 100 focus)
UNIVERSE_100 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", 
    "ITC.NS", "HUL.NS", "LTIM.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS", "ADANIPORTS.NS", 
    "KOTAKBANK.NS", "TITAN.NS", "AXISBANK.NS", "ASIANPAINT.NS", "ULTRACEMCO.NS", "NTPC.NS", "TATAMOTORS.NS", 
    "M&M.NS", "ONGC.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "ADANIPOWER.NS", 
    "TRENT.NS", "HAL.NS", "BEL.NS", "ZOMATO.NS", "VBL.NS", "DLF.NS", "SIEMENS.NS", "GRASIM.NS", "HINDALCO.NS", 
    "NESTLEIND.NS", "SBILIFE.NS", "BAJAJ-AUTO.NS", "WIPRO.NS", "TECHM.NS", "EICHERMOT.NS", "INDUSINDBK.NS", 
    "DIVISLAB.NS", "BPCL.NS", "CIPLA.NS", "HCLTECH.NS", "GAIL.NS", "PNB.NS", "IRFC.NS", "RECLTD.NS", "PFC.NS",
    "IOC.NS", "TATAELXSI.NS", "POLYCAB.NS", "CANBK.NS", "CHOLAFIN.NS", "SHREECEM.NS", "BAJAJHLDNG.NS",
    "DLF.NS", "LODHA.NS", "TATACOMM.NS", "JINDALSTEL.NS", "AMBUJACEM.NS", "ABB.NS", "HAVELLS.NS"
] # Expanded list - add more to reach full 100

# --- 2. DATA PROCESSING ENGINES ---
@st.cache_data(ttl=86400)
def fetch_market_health():
    nifty = yf.download("^NSEI", period="1y", interval="1d")['Close'].squeeze()
    curr, dma = float(nifty.iloc[-1]), float(nifty.rolling(window=200).mean().iloc[-1])
    return curr, dma, (float(nifty.iloc[-1])/float(nifty.iloc[-126]))-1

def get_performance_data(ledger, sector_idx_ticker):
    # Ensure Date is parsed
    ledger['Date'] = pd.to_datetime(ledger['Date'])
    tickers = ledger['Ticker'].unique().tolist()
    tickers_ns = [f"{t}.NS" for t in tickers]
    data = yf.download(tickers_ns + ["^NSEI", sector_idx_ticker], period="1y", interval="1d")['Close']
    
    start_date = ledger['Date'].min()
    daily_values, daily_invested = [], []
    
    for date in data.loc[start_date:].index:
        current_holdings = ledger[ledger['Date'] <= date]
        value = sum(current_holdings['Qty'] * data.loc[date, f"{current_holdings.iloc[i]['Ticker']}.NS"] for i in range(len(current_holdings)))
        invested = current_holdings['Total_Value'].sum()
        daily_values.append(value)
        daily_invested.append(invested)
        
    performance = pd.DataFrame({
        "Date": data.loc[start_date:].index,
        "Portfolio": (np.array(daily_values) / np.array(daily_invested)) - 1,
        "Nifty 50": (data.loc[start_date:, "^NSEI"] / data.loc[start_date, "^NSEI"]) - 1,
        "Tax-Adjusted Goal (9.54%)": (1 + TAX_ADJUSTED_BENCHMARK)**((data.loc[start_date:].index - start_date).days / 365) - 1
    })
    return performance

def run_full_analysis():
    c_nifty, dma, n_ret = fetch_market_health()
    # 14-day smoothing requires 1y + 14d data
    s_data = yf.download(UNIVERSE_100, period="1y", interval="1d")['Close']
    
    # Calculate Smoothed Metrics (14-day Rolling Average)
    m_6m_raw = (s_data / s_data.shift(126)) - 1
    m_6m_smooth = m_6m_raw.rolling(window=14).mean()
    
    vol_raw = s_data.pct_change().rolling(window=126).std() * np.sqrt(252)
    vol_smooth = vol_raw.rolling(window=14).mean()
    
    efficiency_smooth = m_6m_smooth / vol_smooth
    
    results = []
    for t in UNIVERSE_100:
        try:
            score = efficiency_smooth[t].iloc[-1]
            mom = m_6m_smooth[t].iloc[-1]
            
            # Simple PE logic for Top 100
            verdict = "💎 ELITE" if (mom > n_ret and score > 0.8) else ("✅ STABLE" if score > 0.4 else "🛑 WEAK")
            
            results.append({
                "Ticker": t.replace(".NS",""), 
                "Verdict": verdict, 
                "Momentum (6M Smoothed)": mom,
                "Efficiency (Smoothed)": score
            })
        except: continue
    return pd.DataFrame(results).sort_values("Efficiency (Smoothed)", ascending=False).reset_index(drop=True), c_nifty, dma, n_ret

# --- 3. UI LAYOUT ---
st.title("🛡️ EMI-Shield: Master Alpha Cockpit")

with st.expander("📖 DETAILED STRATEGY & TAX-ADJUSTED GOALS", expanded=True):
    st.markdown(f"""
    **Mission:** Offset the **{LOAN_APR*100:.2f}% Loan APR** after-tax.
    - **Tax-Adjusted Target:** **{TAX_ADJUSTED_BENCHMARK*100:.2f}%** (Covers loan cost + 20% STCG tax).
    - **Fortnightly SIP:** ₹{FORTNIGHTLY_SIP:,.0f} (Split into top 3 @ ₹{PER_STOCK_SIP:,.0f} each).
    - **Stability Filter:** We now use a **14-day Moving Average** for all recommendations to prevent daily noise from changing your trades.
    """)

# MARKET HEALTH METRICS
curr_n, dma_n, n_ret_val = fetch_market_health()
m1, m2, m3 = st.columns(3)
m1.metric("Market Status", "🟢 BULLISH" if curr_n > dma_n else "🟡 CAUTION", f"Nifty: {curr_n:,.0f}")
m2.metric("200-Day Safety Line", f"{dma_n:,.0f}")
m3.metric("Nifty 6M (Smooth)", f"{n_ret_val*100:.1f}%")

# --- SECTION 1: PERFORMANCE ---
st.header("📈 Portfolio Performance vs Tax-Adjusted Target")
try:
    ledger = pd.read_csv(SHEET_URL)
    perf_df = get_performance_data(ledger, "^NSEI")
    fig = px.line(perf_df, x="Date", y=["Portfolio", "Nifty 50", "Tax-Adjusted Goal (9.54%)"], 
                  title="Returns vs Tax-Adjusted Loan Cost (%)")
    fig.update_traces(line=dict(dash='dash', color='red'), selector=dict(name="Tax-Adjusted Goal (9.54%)"))
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("💡 Ensure your Google Sheet has a 'Date' column (YYYY-MM-DD) to see the chart.")

# --- SECTION 2: AUDIT ---
st.divider()
st.header("♻️ Strategy Portfolio Audit (14-Day Smoothed)")
if st.button("🔍 AUDIT CURRENT HOLDINGS"):
    try:
        ledger = pd.read_csv(SHEET_URL)
        analysis_df, _, _, _ = run_full_analysis()
        my_holdings = ledger.merge(analysis_df, on="Ticker", how="left")
        my_holdings['Action'] = my_holdings['Verdict'].apply(lambda x: "🛑 SELL & RECYCLE" if x == "🛑 WEAK" else "💎 HOLD")
        st.dataframe(my_holdings[['Ticker', 'Action', 'Momentum (6M Smoothed)', 'Efficiency (Smoothed)']], use_container_width=True)
    except: st.error("Audit failed. Check ticker names in your Sheet.")

# --- SECTION 3: DEPLOYMENT ---
st.divider()
st.header(f"🎯 Fortnightly Deployment: Fresh ₹{FORTNIGHTLY_SIP:,.0f}")
if st.button("🚀 RUN TOP 100 ALPHA SCAN"):
    analysis_df, _, _, _ = run_full_analysis()
    elites = analysis_df[analysis_df['Verdict'] == "💎 ELITE"].head(3)
    if not elites.empty:
        st.success(f"**Action:** Invest ₹{PER_STOCK_SIP:,.0f} each into these Top 3:")
        cols = st.columns(3)
        for i, (idx, row) in enumerate(elites.iterrows()):
            cols[i].metric(row['Ticker'], f"₹{PER_STOCK_SIP}", f"Score: {row['Efficiency (Smoothed)']:.2f}")
    st.dataframe(analysis_df, use_container_width=True)
