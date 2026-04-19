import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- 1. SETTINGS & DYNAMIC CONFIG ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")

# Replace this with your Google Sheet "Published CSV" link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv" # Share > Publish to Web > CSV

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
SECTOR_INDICES = {"Nifty 50": "^NSEI", "Banking": "^NSEBANK", "IT": "^CNXIT", "Auto": "^CNXAUTO", "Pharma": "^CNXPHARMA", "Metal": "^CNXMETAL", "FMCG": "^CNXFMCG", "Realty": "^CNXREALTY"}
ALL_TICKERS = [t for sub in SECTOR_MAP.values() for t in sub]

# --- 2. DATA PROCESSING ENGINES ---
@st.cache_data(ttl=86400)
def fetch_market_health():
    nifty = yf.download("^NSEI", period="1y", interval="1d")['Close'].squeeze()
    curr, dma = float(nifty.iloc[-1]), float(nifty.rolling(window=200).mean().iloc[-1])
    return curr, dma, (float(nifty.iloc[-1])/float(nifty.iloc[-126]))-1

def run_full_analysis():
    c_nifty, dma, n_ret = fetch_market_health()
    s_data = yf.download(ALL_TICKERS, period="1y", interval="1wk")['Close']
    
    fundas = {}
    for t in ALL_TICKERS:
        try:
            info = yf.Ticker(t).info
            fundas[t] = {"PE": info.get('trailingPE', 0), "Sector": [k for k,v in SECTOR_MAP.items() if t in v][0]}
        except: continue
    f_df = pd.DataFrame(fundas).T
    sec_medians = f_df.groupby("Sector")["PE"].median()

    results = []
    for t in ALL_TICKERS:
        try:
            m_6m = (s_data[t].iloc[-1] / s_data[t].iloc[-26]) - 1
            vol = s_data[t].pct_change().std() * np.sqrt(52)
            score = m_6m / vol
            pe = f_df.loc[t, "PE"]
            s_pe = sec_medians[f_df.loc[t, "Sector"]]
            
            if m_6m > n_ret and score > 0.8 and pe < s_pe * 1.6: verdict = "💎 ELITE"
            elif score > 0.4: verdict = "✅ STABLE"
            else: verdict = "🛑 WEAK"
            
            results.append({
                "Ticker": t.replace(".NS",""), 
                "Sector": f_df.loc[t, "Sector"], 
                "Verdict": verdict, 
                "Momentum (6M)": m_6m,
                "Efficiency": score, 
                "PE": pe, 
                "Peer Median": s_pe
            })
        except: continue
    
    df = pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)
    df.index += 1
    return df, c_nifty, dma, n_ret

# --- 3. UI LAYOUT ---
st.title("🛡️ EMI-Shield: Master Alpha Cockpit")

with st.expander("📖 DETAILED STRATEGY & GOALS", expanded=True):
    st.markdown("""
    **Core Objective:** Generate **12-14% XIRR** to offset a **7.65% Car Loan**.
    - **Fresh SIP:** Invest **₹25,000 every fortnight**. Split ₹8,333 each into the top 3 'Elite' picks.
    - **Safety Switch:** If Nifty < 200-DMA, hold cash.
    - **Alpha Rule:** Only buy stocks growing faster than the Nifty 50 over 6 months.
    - **Efficiency Rule:** Prioritize stocks with smooth uptrends (High Sharpe Ratio) to minimize volatility stress.
    """)

# MARKET HEALTH METRICS
c_nifty, dma_nifty, n_ret = fetch_market_health()
m1, m2, m3 = st.columns(3)
m1.metric("Market Status", "🟢 BULLISH" if c_nifty > dma_nifty else "🟡 CAUTION", f"Nifty: {c_nifty:,.0f}")
m2.metric("200-Day Safety Line", f"{dma_nifty:,.0f}")
m3.metric("Nifty 6M Return", f"{n_ret*100:.1f}%")

# --- SECTION 1: PERFORMANCE VS SECTORS ---
st.header("📈 Portfolio Performance Tracker")
sel_sector = st.selectbox("Compare your Strategy against Sector:", list(SECTOR_INDICES.keys()))
try:
    ledger = pd.read_csv(SHEET_URL)
    st.info("Performance Chart will render here once Google Sheet data is live.")
except:
    st.info("💡 Connect your Google Sheet to see performance charts.")

# --- SECTION 2: THE RECYCLE ENGINE (MANAGING EXISTING BUYS) ---
st.divider()
st.header("♻️ Strategy Portfolio Audit (Recycle Engine)")
st.write("This section analyzes the stocks you've already bought using this plan to decide if you should Hold or Sell.")

if st.button("🔍 AUDIT CURRENT HOLDINGS"):
    try:
        ledger = pd.read_csv(SHEET_URL)
        analysis_df, _, _, _ = run_full_analysis()
        
        # Merge ledger with current analysis
        my_holdings = ledger.merge(analysis_df, on="Ticker", how="left")
        
        def audit_action(row):
            if row['Verdict'] == "🛑 WEAK": return "🛑 SELL & RECYCLE"
            if row['Verdict'] == "✅ STABLE": return "💎 HOLD"
            return "🔥 ELITE HOLD"

        my_holdings['Action'] = my_holdings.apply(audit_action, axis=1)
        
        st.dataframe(
            my_holdings[['Ticker', 'Verdict', 'Action', 'Momentum (6M)', 'Efficiency', 'PE']], 
            use_container_width=True,
            column_config={
                "Momentum (6M)": st.column_config.NumberColumn(format="%.1f%%"),
                "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2)
            }
        )
        
        to_recycle = my_holdings[my_holdings['Action'] == "🛑 SELL & RECYCLE"]
        if not to_recycle.empty:
            st.error(f"⚠️ **Action Required:** Sell {', '.join(to_recycle['Ticker'].tolist())}. Move proceeds to today's Top Elite pick.")
        else:
            st.success("✅ All strategy holdings are currently healthy. No selling required.")
    except:
        st.error("Could not find holdings. Ensure your Google Sheet Ticker column matches the Ticker names here (e.g., TRENT, not TRENT.NS).")

# --- SECTION 3: DEPLOYMENT (NEW ₹25K) ---
st.divider()
st.header("🎯 Fortnightly Deployment: Fresh ₹25,000")
if st.button("🚀 RUN GLOBAL ALPHA SCAN"):
    analysis_df, _, _, _ = run_full_analysis()
    
    # Deployment Instructions
    elites = analysis_df[analysis_df['Verdict'] == "💎 ELITE"].head(3)
    if not elites.empty:
        st.success("**Instructions:** Invest ₹8,333 each into these Top 3:")
        cols = st.columns(3)
        for i, (idx, row) in enumerate(elites.iterrows()):
            cols[i].metric(row['Ticker'], "₹8,333", f"Score: {row['Efficiency']:.2f}")
    
    st.subheader("Full 50-Stock Market Rankings")
    st.dataframe(analysis_df, use_container_width=True, column_config={
        "Momentum (6M)": st.column_config.ProgressColumn(min_value=-0.1, max_value=1.0),
        "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
        "PE": st.column_config.NumberColumn("Stock PE"),
        "Peer Median": st.column_config.NumberColumn("Peer Median")
    })

# --- SECTION 4: LAYMAN'S GLOSSARY ---
st.divider()
st.header("📚 The Investor's Dictionary (Layman Edition)")
g1, g2 = st.columns(2)
with g1:
    with st.expander("📈 XIRR (Extended Internal Rate of Return)", expanded=True):
        st.write("**Full Form:** Extended Internal Rate of Return.")
        st.write("**Layman Terms:** Your 'Personal Interest Rate'. It accounts for the fact that you invest ₹25k at different dates. If this is higher than 7.65%, you are beating your car loan cost.")
        st.latex(r"XIRR \text{ Goal: } 12\%+")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("**Full Form:** Relative Strength / Positive Alpha.")
        st.write("**Layman Terms:** 'The Speedometer'. Does this stock run faster than the Nifty 50? If Nifty grows 2% and your stock grows 5%, your Alpha is 3%.")
        st.write("**Formula:** $Alpha = R_p - [R_f + \beta(R_m - R_f)]$")
with g2:
    with st.expander("🎯 Efficiency (Sharpe Ratio)", expanded=True):
        st.write("**Full Form:** Risk-Adjusted Return.")
        st.write("**Layman Terms:** 'The Smoothness Score'. We want stocks that go up in a straight line, not ones that jump up and down violently. High score = Smooth ride.")
        st.latex(r"Efficiency = \frac{R_p - R_f}{\sigma_p}")
    with st.expander("🛡️ 200-DMA"):
        st.write("**Full Form:** 200-Day Moving Average.")
        st.write("**Layman Terms:** 'The Health Line'. If the Nifty is below this average price, the market is 'sick' and we hold cash to protect your EMI.")
        st.write("**Formula:** $200DMA = \frac{\sum_{i=1}^{200} P_i}{200}$")
