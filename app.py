import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- CONFIG & DYNAMIC SECTOR MAP ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" # Share > Publish to Web > CSV

SECTOR_INDICES = {
    "Nifty 50": "^NSEI",
    "Banking": "^NSEBANK",
    "IT": "^CNXIT",
    "Auto": "^CNXAUTO",
    "Pharma": "^CNXPHARMA",
    "Metal": "^CNXMETAL",
    "FMCG": "^CNXFMCG",
    "Realty": "^CNXREALTY"
}

SECTOR_MAP = {
    "Banking/Finance": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "BAJFINANCE.NS", "SBILIFE.NS", "LICI.NS"],
    "IT Services": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "LTIM.NS", "TECHM.NS"],
    "Auto/Mobility": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "EICHERMOT.NS", "BAJAJ-AUTO.NS"],
    "FMCG/Retail": ["ITC.NS", "HUL.NS", "NESTLEIND.NS", "VBL.NS", "TRENT.NS", "ZOMATO.NS", "TITAN.NS"],
    "Energy/Power": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "NTPC.NS", "POWERGRID.NS", "ADANIPOWER.NS", "COALINDIA.NS"],
    "Industrial/Defense": ["HAL.NS", "BEL.NS", "SIEMENS.NS", "ADANIPORTS.NS"],
    "Materials/Const": ["JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS", "ULTRACEMCO.NS", "GRASIM.NS", "DLF.NS"],
    "Healthcare": ["SUNPHARMA.NS", "CIPLA.NS", "DIVISLAB.NS"]
}

ALL_TICKERS = [t for sub in SECTOR_MAP.values() for t in sub]

# --- DATA ENGINES ---
@st.cache_data(ttl=86400)
def fetch_market_context():
    nifty = yf.download("^NSEI", period="1y", interval="1d")['Close'].squeeze()
    return float(nifty.iloc[-1]), float(nifty.rolling(window=200).mean().iloc[-1]), (nifty.iloc[-1]/nifty.iloc[-126])-1

def get_performance_data(ledger, sector_idx_ticker):
    # Fetch historical data for all tickers in ledger
    tickers = ledger['Ticker'].unique().tolist()
    tickers_ns = [f"{t}.NS" for t in tickers]
    data = yf.download(tickers_ns + ["^NSEI", sector_idx_ticker], period="1y", interval="1d")['Close']
    
    # Calculate Portfolio Value Over Time
    start_date = pd.to_datetime(ledger['Date']).min()
    daily_values = []
    daily_invested = []
    
    for date in data.loc[start_date:].index:
        current_holdings = ledger[pd.to_datetime(ledger['Date']) <= date]
        value = sum(current_holdings['Qty'] * data.loc[date, f"{t}.NS"] for t in current_holdings['Ticker'])
        invested = current_holdings['Total_Value'].sum()
        daily_values.append(value)
        daily_invested.append(invested)
        
    performance = pd.DataFrame({
        "Date": data.loc[start_date:].index,
        "Portfolio": (np.array(daily_values) / np.array(daily_invested)) - 1,
        "Nifty 50": (data.loc[start_date:, "^NSEI"] / data.loc[start_date, "^NSEI"]) - 1,
        "Sector": (data.loc[start_date:, sector_idx_ticker] / data.loc[start_date, sector_idx_ticker]) - 1
    })
    return performance

# --- DASHBOARD UI ---
st.title("🛡️ EMI-Shield: Executive Alpha Dashboard")

with st.expander("📖 STRATEGY & RISK PROTOCOLS", expanded=False):
    st.markdown("""
    **Mission:** 12% XIRR via ₹25,000 Fortnightly SIP.
    - **Selection:** High Efficiency (Return ÷ Risk) + Positive Alpha vs Nifty.
    - **Deployment:** Split ₹25k into Top 3 'Elite' picks (~₹8,333 each).
    - **Protection:** Sell 'Weak' holdings; Hold cash if Nifty < 200-DMA.
    """)

# 1. PERFORMANCE TRACKING
st.header("📈 Relative Performance Engine")
sel_sector = st.selectbox("Compare Portfolio against Sector:", list(SECTOR_INDICES.keys()))

try:
    ledger = pd.read_csv(SHEET_URL)
    perf_df = get_performance_data(ledger, SECTOR_INDICES[sel_sector])
    
    fig = px.line(perf_df, x="Date", y=["Portfolio", "Nifty 50", "Sector"], 
                  title="Cumulative Returns Comparison (%)",
                  labels={"value": "Return %", "variable": "Benchmark"})
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Performance chart will activate once you log your first trade in Google Sheets.")

# 2. MARKET SCAN (ACTION)
st.divider()
st.header("🎯 Fortnightly Deployment (₹25,000)")
if st.button("🚀 EXECUTE 50-STOCK ALPHA SCAN"):
    c_nifty, dma, n_ret = fetch_market_context()
    
    # Run Analysis
    raw_data = yf.download(ALL_TICKERS, period="1y", interval="1wk")['Close']
    fundas = {t: {"PE": yf.Ticker(t).info.get('trailingPE', 0), 
                  "Sector": [k for k,v in SECTOR_MAP.items() if t in v][0]} for t in ALL_TICKERS}
    f_df = pd.DataFrame(fundas).T
    sec_medians = f_df.groupby("Sector")["PE"].median()

    results = []
    for t in ALL_TICKERS:
        try:
            m_6m = (raw_data[t].iloc[-1] / raw_data[t].iloc[-26]) - 1
            vol = raw_data[t].pct_change().std() * np.sqrt(52)
            score = m_6m / vol
            pe = f_df.loc[t, "PE"]
            s_pe = sec_medians[f_df.loc[t, "Sector"]]
            
            verdict = "💎 ELITE" if (m_6m > n_ret and score > 0.8 and pe < s_pe * 1.5) else ("✅ STABLE" if score > 0.4 else "🛑 WEAK")
            
            results.append({"Ticker": t.replace(".NS",""), "Sector": f_df.loc[t, "Sector"], "Verdict": verdict, 
                            "Efficiency": score, "PE": pe, "Sect. Median": s_pe})
        except: continue
    
    df = pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)
    df.index += 1
    
    # Top Picks
    elites = df[df['Verdict'] == "💎 ELITE"].head(3)
    if not elites.empty:
        cols = st.columns(3)
        for i, (idx, row) in enumerate(elites.iterrows()):
            cols[i].success(f"**{row['Ticker']}**\n\nInvest: ₹8,333\n\nEfficiency: {row['Efficiency']:.2f}")
    
    st.dataframe(df, use_container_width=True, column_config={
        "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
        "PE": st.column_config.NumberColumn("Your PE"),
        "Sect. Median": st.column_config.NumberColumn("Peer Median")
    })

# 3. GLOSSARY
st.divider()
st.subheader("📚 Investor Glossary")
c_a, c_b = st.columns(2)
with c_a:
    st.write("**Efficiency:** Risk-adjusted return. Since you have a large EMI, you want a 'smooth ride' (>0.8).")
    st.write("**Sect. Median:** Dynamic fair-value for that specific industry today.")
with c_b:
    st.write("**Alpha:** Outperforming the Nifty. If your 'Portfolio' line in the chart is above the 'Nifty 50' line, you have Alpha.")
    st.write("**200-DMA:** The long-term trend line. We play defense if the market falls below this.")
