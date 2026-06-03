import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- 1. SETTINGS & CONSTANTS ---
st.set_page_config(page_title="EMI-Shield Global Cockpit", layout="wide")

LOAN_APR = 0.0763  
TAX_ADJUSTED_TARGET = 0.0954 
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 6667 
SHEET_URL = "YOUR_GOOGLE_SHEET_CSV_LINK" 

# GLOBAL UNIVERSE (India Top 75 + US Top 25)
INDIAN_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "BHARTIARTL.NS", "SBIN.NS", "LICI.NS", 
    "ITC.NS", "HUL.NS", "LTIM.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS", "ADANIPORTS.NS", 
    "KOTAKBANK.NS", "TITAN.NS", "AXISBANK.NS", "ASIANPAINT.NS", "ULTRACEMCO.NS", "NTPC.NS", "TATAMOTORS.NS", 
    "M&M.NS", "ONGC.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "ADANIPOWER.NS", 
    "TRENT.NS", "HAL.NS", "BEL.NS", "ZOMATO.NS", "VBL.NS", "DLF.NS", "SIEMENS.NS", "GRASIM.NS", "HINDALCO.NS", 
    "NESTLEIND.NS", "SBILIFE.NS", "BAJAJ-AUTO.NS", "WIPRO.NS", "TECHM.NS", "EICHERMOT.NS", "INDUSINDBK.NS", 
    "DIVISLAB.NS", "BPCL.NS", "CIPLA.NS", "HCLTECH.NS", "GAIL.NS", "PNB.NS", "IRFC.NS", "RECLTD.NS", "PFC.NS",
    "IOC.NS", "TATAELXSI.NS", "POLYCAB.NS", "CANBK.NS", "CHOLAFIN.NS", "SHREECEM.NS", "BAJAJHLDNG.NS",
    "LODHA.NS", "TATACOMM.NS", "JINDALSTEL.NS", "AMBUJACEM.NS", "ABB.NS", "HAVELLS.NS", "PIDILITIND.NS",
    "TATACONSUM.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "GODREJCP.NS", "MAZDOCK.NS", "RVNL.NS", "IRCTC.NS"
]

US_STOCKS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "PEP", 
    "ADBE", "CSCO", "NFLX", "AMD", "TMUS", "INTC", "TXN", "QCOM", "INTU", "AMAT", 
    "HON", "ISRG", "SBUX", "BKNG", "MDLZ"
]
UNIVERSE = INDIAN_STOCKS + US_STOCKS

# --- 2. DATA ENGINES ---
@st.cache_data(ttl=86400)
def fetch_macro_and_markets():
    # Macro Indicators
    macro = yf.download(["^NSEI", "^NDX", "^INDIAVIX", "INR=X"], period="1y", interval="1d")['Close']
    stocks = yf.download(UNIVERSE, period="1y", interval="1d")['Close']
    return macro, stocks

def analyze_markets(macro, stocks):
    # MACRO HEALTH
    nifty = macro["^NSEI"].dropna()
    vix = macro["^INDIAVIX"].dropna()
    usd_inr = macro["INR=X"].dropna()
    
    macro_status = {
        "Nifty_Trend": "🟢" if nifty.iloc[-1] > nifty.rolling(200).mean().iloc[-1] else "🔴",
        "VIX_Level": "🟢 (Calm)" if vix.iloc[-1] < 15 else ("🟡 (Elevated)" if vix.iloc[-1] < 22 else "🔴 (Panic)"),
        "VIX_Val": vix.iloc[-1],
        "USD_INR": usd_inr.iloc[-1],
        "Global_Clear": True if (nifty.iloc[-1] > nifty.rolling(200).mean().iloc[-1]) and (vix.iloc[-1] < 22) else False
    }

    # STOCK ANALYSIS (14-Day Smoothing)
    m_6m = ((stocks / stocks.shift(126)) - 1).rolling(14).mean()
    vol = (stocks.pct_change().rolling(126).std() * np.sqrt(252)).rolling(14).mean()
    efficiency = (m_6m / vol).iloc[-1]
    
    # Benchmarks
    n_ret = ((nifty.iloc[-1] / nifty.iloc[-126]) - 1)
    ndx_ret = ((macro["^NDX"].dropna().iloc[-1] / macro["^NDX"].dropna().iloc[-126]) - 1)
    
    results = []
    for t in UNIVERSE:
        try:
            is_us = t in US_STOCKS
            bench_ret = ndx_ret if is_us else n_ret
            score = efficiency[t]
            
            # Dynamic Stop Loss (15% below 52-week High)
            high_52w = stocks[t].max()
            current_price = stocks[t].iloc[-1]
            stop_loss = high_52w * 0.85
            dist_to_stop = ((current_price - stop_loss) / current_price) * 100
            
            verdict = "💎 ELITE" if (m_6m[t].iloc[-1] > bench_ret and score > 0.8) else ("✅ STABLE" if score > 0.4 else "🛑 WEAK")
            
            results.append({
                "Ticker": t.replace(".NS",""), 
                "Region": "US" if is_us else "India",
                "Verdict": verdict, 
                "Efficiency": score, 
                "Price": current_price,
                "Stop-Loss Level": stop_loss,
                "Buffer to SL": f"{dist_to_stop:.1f}%"
            })
        except: continue
        
    df = pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)
    df.index += 1
    return df, macro_status

# --- UI SECTION ---
st.title("🌍 EMI-Shield: Global Macro Cockpit")

# 1. MACRO DASHBOARD
macro_data, stock_data = fetch_macro_and_markets()
analysis_df, m_status = analyze_markets(macro_data, stock_data)

st.header("🧭 Global Macro Environment")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Nifty 50 Trend", m_status["Nifty_Trend"])
c2.metric("India VIX (Fear Gauge)", m_status["VIX_Level"], f"{m_status['VIX_Val']:.1f}")
c3.metric("USD/INR", f"₹{m_status['USD_INR']:.2f}")
if m_status["Global_Clear"]:
    c4.success("🟢 ALL CLEAR FOR DEPLOYMENT")
else:
    c4.error("🔴 MACRO WARNING: HOLD CASH")

# 2. PERFORMANCE CHART
st.divider()
st.header("📈 Global Portfolio Returns vs Targets")
try:
    ledger = pd.read_csv(SHEET_URL)
    ledger['Date'] = pd.to_datetime(ledger['Date'], dayfirst=False)
    
    start_date = ledger['Date'].min()
    dates = macro_data["^NSEI"].dropna().loc[start_date:].index
    port_vals = []
    
    for d in dates:
        active = ledger[ledger['Date'] <= d]
        if active.empty:
            port_vals.append(0)
            continue
        
        val = 0
        for _, row in active.iterrows():
            ticker = row['Ticker']
            t_mapped = f"{ticker}.NS" if ticker in [t.replace(".NS","") for t in INDIAN_STOCKS] else ticker
            try: val += row['Qty'] * stock_data.loc[d, t_mapped]
            except: pass
            
        invested = active['Total_Value'].sum()
        port_vals.append((val / invested) - 1 if invested > 0 else 0)
        
    perf = pd.DataFrame({
        "Date": dates, 
        "Portfolio": port_vals, 
        "Nifty 50 (India)": (macro_data["^NSEI"].dropna().loc[start_date:] / macro_data["^NSEI"].dropna().loc[start_date].iloc[0]) - 1,
        "NASDAQ 100 (US)": (macro_data["^NDX"].dropna().loc[start_date:] / macro_data["^NDX"].dropna().loc[start_date].iloc[0]) - 1,
        "Tax-Adj Goal (9.54%)": (1 + TAX_ADJUSTED_TARGET)**((dates - start_date).days/365) - 1
    })
    
    fig = px.line(perf, x="Date", y=["Portfolio", "Nifty 50 (India)", "NASDAQ 100 (US)", "Tax-Adj Goal (9.54%)"])
    fig.update_traces(line=dict(dash='dash', color='red'), selector=dict(name="Tax-Adj Goal (9.54%)"))
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("💡 Chart requires Google Sheet with columns: Date, Ticker, Qty, BuyPrice, Total_Value")

# 3. AUDIT & STOP-LOSS ENGINE
st.divider()
st.header("🛡️ Portfolio Audit & Stop-Loss Engine")
if st.button("🔍 AUDIT CURRENT HOLDINGS"):
    try:
        ledger = pd.read_csv(SHEET_URL)
        audit = ledger.merge(analysis_df, on="Ticker", how="left")
        
        def audit_action(row):
            if float(row['Buffer to SL'].strip('%')) <= 0: return "🚨 STOP-LOSS HIT: SELL"
            if row['Verdict'] == "🛑 WEAK": return "🛑 RECYCLE (SELL)"
            return "💎 HOLD"
            
        audit['Action'] = audit.apply(audit_action, axis=1)
        st.dataframe(audit[['Ticker', 'Region', 'Action', 'Efficiency', 'Price', 'Stop-Loss Level', 'Buffer to SL']], use_container_width=True)
        
        to_sell = audit[audit['Action'].str.contains("SELL")]
        if not to_sell.empty:
            st.error(f"Action Required: Sell {', '.join(to_sell['Ticker'].tolist())}")
    except: st.error("Audit failed. Check Google Sheet.")

# 4. GLOBAL DEPLOYMENT
st.divider()
st.header(f"🎯 Global Deployment: Fresh ₹{FORTNIGHTLY_SIP}")
if st.button("🚀 RUN GLOBAL ALPHA SCAN"):
    if not m_status["Global_Clear"]:
        st.warning("⚠️ Macro Indicators are flashing Red. We recommend pausing deployments and holding cash this fortnight to protect your EMI reserves.")
    
    st.subheader("Top Global Elite Picks")
    elites = analysis_df[analysis_df['Verdict'] == "💎 ELITE"].head(3)
    cols = st.columns(3)
    for i, (idx, row) in enumerate(elites.iterrows()):
        cols[i].metric(f"{row['Ticker']} ({row['Region']})", f"₹{PER_STOCK_SIP}", f"Buffer to SL: {row['Buffer to SL']}")
    
    st.dataframe(analysis_df, column_config={
        "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
        "Price": st.column_config.NumberColumn(format="%.2f")
    }, use_container_width=True)
