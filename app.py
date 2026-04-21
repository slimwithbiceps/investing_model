import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- 1. SETTINGS & DYNAMIC CONFIG ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")

# LOAN CONSTANTS (From Indian Bank Sanction April 2026)
LOAN_APR = 0.0763  # 7.63% APR[cite: 1]
EMI_AMOUNT = 40573 #[cite: 1, 2]
TOTAL_INTEREST = 414362 #[cite: 1]

# Replace this with your Google Sheet "Published CSV" link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv"

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

def get_performance_data(ledger, sector_idx_ticker):
    tickers = ledger['Ticker'].unique().tolist()
    tickers_ns = [f"{t}.NS" for t in tickers]
    data = yf.download(tickers_ns + ["^NSEI", sector_idx_ticker], period="1y", interval="1d")['Close']
    
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
        "Sector": (data.loc[start_date:, sector_idx_ticker] / data.loc[start_date, sector_idx_ticker]) - 1,
        "Loan Benchmark (7.63%)": (1 + LOAN_APR)**((data.loc[start_date:].index - start_date).days / 365) - 1
    })
    return performance

def run_full_analysis():
    c_nifty, dma, n_ret = fetch_market_health()
    s_data = yf.download(ALL_TICKERS, period="1y", interval="1wk")['Close']
    fundas = {t: {"PE": yf.Ticker(t).info.get('trailingPE', 0), "Sector": [k for k,v in SECTOR_MAP.items() if t in v][0]} for t in ALL_TICKERS}
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
            verdict = "💎 ELITE" if (m_6m > n_ret and score > 0.8 and pe < s_pe * 1.6) else ("✅ STABLE" if score > 0.4 else "🛑 WEAK")
            results.append({"Ticker": t.replace(".NS",""), "Sector": f_df.loc[t, "Sector"], "Verdict": verdict, "Momentum (6M)": m_6m, "Efficiency": score, "PE": pe, "Peer Median": s_pe})
        except: continue
    return pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True), c_nifty, dma, n_ret

# --- 3. UI LAYOUT ---
st.title("🛡️ EMI-Shield: Master Alpha Cockpit")

with st.expander("📖 DETAILED STRATEGY & LOAN GOALS", expanded=True):
    st.markdown(f"""
    **Mission:** Generate **12-14% XIRR** to offset the **{LOAN_APR*100:.2f}% Loan APR**.
    - **Loan Profile:** ₹20,20,000 sanctioned with an EMI of ₹{EMI_AMOUNT:,.0f}[cite: 1, 2].
    - **Total Interest Burden:** ₹{TOTAL_INTEREST:,.0f} over 5 years[cite: 1].
    - **Break-Even Target:** Your portfolio line must stay above the **Loan Benchmark** line in the chart below to effectively pay for your car's interest.
    """)

# MARKET HEALTH METRICS
curr_n, dma_n, n_ret_val = fetch_market_health()
m1, m2, m3 = st.columns(3)
m1.metric("Market Status", "🟢 BULLISH" if curr_n > dma_n else "🟡 CAUTION", f"Nifty: {curr_n:,.0f}")
m2.metric("200-Day Safety Line", f"{dma_n:,.0f}")
m3.metric("Nifty 6M Return", f"{n_ret_val*100:.1f}%")

# --- SECTION 1: PERFORMANCE VS LOAN ---
st.header("📈 Portfolio Performance vs Loan Benchmark")
sel_sector = st.selectbox("Compare Strategy against Sector & Loan:", list(SECTOR_INDICES.keys()))
try:
    ledger = pd.read_csv(SHEET_URL)
    perf_df = get_performance_data(ledger, SECTOR_INDICES[sel_sector])
    fig = px.line(perf_df, x="Date", y=["Portfolio", "Nifty 50", "Sector", "Loan Benchmark (7.63%)"], 
                  title="Cumulative Returns vs Loan Cost (%)",
                  labels={"value": "Return %", "variable": "Benchmark"})
    # Color the Loan Benchmark distinctly
    fig.update_traces(line=dict(dash='dash', color='red'), selector=dict(name="Loan Benchmark (7.63%)"))
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("💡 Performance Chart will render here once Google Sheet data is live.")

# --- SECTION 2: THE RECYCLE ENGINE ---
st.divider()
st.header("♻️ Strategy Portfolio Audit (Recycle Engine)")
if st.button("🔍 AUDIT CURRENT HOLDINGS"):
    try:
        ledger = pd.read_csv(SHEET_URL)
        analysis_df, _, _, _ = run_full_analysis()
        my_holdings = ledger.merge(analysis_df, on="Ticker", how="left")
        def audit_action(row):
            if row['Verdict'] == "🛑 WEAK": return "🛑 SELL & RECYCLE"
            return "💎 HOLD" if row['Verdict'] == "✅ STABLE" else "🔥 ELITE HOLD"
        my_holdings['Action'] = my_holdings.apply(audit_action, axis=1)
        st.dataframe(my_holdings[['Ticker', 'Verdict', 'Action', 'Momentum (6M)', 'Efficiency', 'PE']], use_container_width=True,
                     column_config={"Momentum (6M)": st.column_config.NumberColumn(format="%.1f%%"), "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2)})
        to_recycle = my_holdings[my_holdings['Action'] == "🛑 SELL & RECYCLE"]
        if not to_recycle.empty:
            st.error(f"⚠️ Action Required: Sell {', '.join(to_recycle['Ticker'].tolist())}. Move proceeds to today's Top Elite pick.")
        else:
            st.success("✅ Strategy holdings are currently healthy.")
    except: st.error("Holdings not found. Ensure Ticker names in Sheet match app (e.g. TRENT).")

# --- SECTION 3: DEPLOYMENT ---
st.divider()
st.header("🎯 Fortnightly Deployment: Fresh ₹25,000")
if st.button("🚀 RUN GLOBAL ALPHA SCAN"):
    analysis_df, _, _, _ = run_full_analysis()
    elites = analysis_df[analysis_df['Verdict'] == "💎 ELITE"].head(3)
    if not elites.empty:
        st.success("**Instructions:** Invest ₹8,333 each into these Top 3:")
        cols = st.columns(3)
        for i, (idx, row) in enumerate(elites.iterrows()):
            cols[i].metric(row['Ticker'], "₹8,333", f"Score: {row['Efficiency']:.2f}")
    st.dataframe(analysis_df, use_container_width=True, column_config={"Momentum (6M)": st.column_config.ProgressColumn(min_value=-0.1, max_value=1.0), "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2), "PE": st.column_config.NumberColumn("Stock PE"), "Peer Median": st.column_config.NumberColumn("Peer Median")})

# --- SECTION 4: LAYMAN'S GLOSSARY ---
st.divider()
st.header("📚 The Investor's Dictionary (Layman Edition)")
g1, g2 = st.columns(2)
with g1:
    with st.expander("📈 XIRR (Extended Internal Rate of Return)", expanded=True):
        st.write("**Full Form:** Extended Internal Rate of Return.")
        st.write(f"**Layman Terms:** Your 'Personal Interest Rate'. If this is higher than **{LOAN_APR*100:.2f}%**, your investments are growing faster than your car loan cost[cite: 1].")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("**Full Form:** Relative Strength / Positive Alpha.")
        st.write("**Layman Terms:** 'The Speedometer'. Does this stock run faster than the Nifty 50?")
with g2:
    with st.expander("🎯 Efficiency (Sharpe Ratio)", expanded=True):
        st.write("**Full Form:** Risk-Adjusted Return.")
        st.write("**Layman Terms:** 'The Smoothness Score'. We want stocks that go up in a smooth ride. High score = Stress-free.")
    with st.expander("🛡️ 200-DMA"):
        st.write("**Full Form:** 200-Day Moving Average.")
        st.write("**Layman Terms:** 'The Health Line'. If Nifty is below this, the market is 'sick'.")
