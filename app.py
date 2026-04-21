import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- 1. SETTINGS & LOAN CONSTANTS ---
st.set_page_config(page_title="EMI-Shield Alpha Cockpit", layout="wide")

LOAN_APR = 0.0763 #
TAX_ADJUSTED_TARGET = 0.0954 
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 6667 
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?output=csv"

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
    "TATACONSUM.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "GODREJCP.NS", "VBL.NS", "BEL.NS", "MAZDOCK.NS",
    "RVNL.NS", "IRCTC.NS", "PAGEIND.NS", "TVSMOTOR.NS", "HEROMOTOCO.NS", "CUMMINSIND.NS", "TRENT.NS",
    "MAXHEALTH.NS", "MANKIND.NS", "BOSCHLTD.NS", "PERSISTENT.NS", "DIXON.NS", "OBEROIRLTY.NS", "TATACHEM.NS",
    "PETRONET.NS", "MRF.NS", "COLPAL.NS", "JUBLFOOD.NS", "BHEL.NS", "NMDC.NS", "AUBANK.NS", "YESBANK.NS"
]

@st.cache_data(ttl=86400)
def fetch_data():
    nifty = yf.download("^NSEI", period="1y", interval="1d")['Close'].squeeze()
    stocks = yf.download(UNIVERSE_100, period="1y", interval="1d")['Close']
    return nifty, stocks

def run_analysis(nifty, stocks):
    # 14-Day Smoothing
    m_6m = ((stocks / stocks.shift(126)) - 1).rolling(14).mean()
    vol = (stocks.pct_change().rolling(126).std() * np.sqrt(252)).rolling(14).mean()
    efficiency = (m_6m / vol).iloc[-1]
    n_ret = ((nifty.iloc[-1] / nifty.iloc[-126]) - 1)
    
    results = []
    for t in UNIVERSE_100:
        try:
            info = yf.Ticker(t).info
            pe = info.get('trailingPE', 0)
            score = efficiency[t]
            verdict = "💎 ELITE" if (m_6m[t].iloc[-1] > n_ret and score > 0.8) else ("✅ STABLE" if score > 0.4 else "🛑 WEAK")
            results.append({"Ticker": t.replace(".NS",""), "Verdict": verdict, "Momentum": m_6m[t].iloc[-1], "Efficiency": score, "PE": pe})
        except: continue
    return pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)

# --- UI ---
st.title("🛡️ EMI-Shield: Master Alpha Cockpit")

# PERFORMANCE CHART
try:
    ledger = pd.read_csv(SHEET_URL)
    ledger['Date'] = pd.to_datetime(ledger['Date'])
    nifty, stocks = fetch_data()
    
    start_date = ledger['Date'].min()
    dates = nifty.loc[start_date:].index
    port_vals = []
    
    for d in dates:
        active = ledger[ledger['Date'] <= d]
        val = sum(active['Qty'] * stocks.loc[d, active['Ticker'] + ".NS"])
        port_vals.append((val / active['Total_Value'].sum()) - 1)
        
    perf = pd.DataFrame({"Date": dates, "Portfolio": port_vals, 
                         "Nifty 50": (nifty.loc[start_date:] / nifty.loc[start_date]) - 1,
                         "Tax-Adj Goal (9.54%)": (1.0954**((dates - start_date).days/365)) - 1})
    st.plotly_chart(px.line(perf, x="Date", y=["Portfolio", "Nifty 50", "Tax-Adj Goal (9.54%)"]))
except:
    st.info("💡 Ensure 'Date' (YYYY-MM-DD) and 'Ticker' (e.g. TRENT) are correct in Google Sheets.")

# DEPLOYMENT
if st.button("🚀 RUN TOP 100 ALPHA SCAN"):
    nifty, stocks = fetch_data()
    df = run_analysis(nifty, stocks)
    st.header(f"🎯 Deployment: ₹{FORTNIGHTLY_SIP}")
    elites = df[df['Verdict'] == "💎 ELITE"].head(3)
    cols = st.columns(3)
    for i, (idx, row) in enumerate(elites.iterrows()):
        cols[i].metric(row['Ticker'], f"₹{PER_STOCK_SIP}", f"Score: {row['Efficiency']:.2f}")
    
    st.dataframe(df, column_config={"Momentum": st.column_config.NumberColumn(format="%.1f%%"), 
                                    "Efficiency": st.column_config.ProgressColumn(min_value=0, max_value=2),
                                    "PE": st.column_config.NumberColumn("PE Ratio")}, use_container_width=True)

# GLOSSARY
st.divider()
st.header("📚 The Investor's Dictionary")
c1, c2 = st.columns(2)
with c1:
    with st.expander("📈 XIRR (Extended Internal Rate of Return)", expanded=True):
        st.write("Your personal interest rate. Accounts for the timing of your ₹20,000 deposits.")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("The speed of a stock. If the market grows 2% and your stock grows 5%, your Alpha is 3%.")
with c2:
    with st.expander("🎯 Efficiency (Sharpe Ratio)", expanded=True):
        st.write("How 'smooth' the climb is. High score means low stress.")
    with st.expander("🛡️ 200-DMA"):
        st.write("The 200-day health line. If Nifty is below this, we protect the car loan by holding cash.")
