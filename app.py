import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os

# --- 1. SETTINGS & LOAN CONSTANTS ---
st.set_page_config(page_title="EMI-Shield Global Cockpit", layout="wide")

LOAN_APR = 0.0763  # 7.63% Indian Bank APR
TAX_RATE = 0.20
TAX_ADJUSTED_TARGET = LOAN_APR / (1 - TAX_RATE)  # 9.54% Gross Target
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 10000  
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?gid=0&single=true&output=csv"

# --- MANUAL CACHE OVERRIDE ---
with st.sidebar:
    st.write("🔧 Developer Tools")
    if st.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.rerun()

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

# --- SUPER-ROBUST HARDCODED SECTOR MAPPING ---
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AMZN": "Consumer Cyclical", 
    "META": "Communication Services", "GOOGL": "Communication Services", "TSLA": "Consumer Cyclical", 
    "AVGO": "Technology", "COST": "Consumer Defensive", "PEP": "Consumer Defensive", "ADBE": "Technology", 
    "CSCO": "Technology", "NFLX": "Communication Services", "AMD": "Technology", "TMUS": "Communication Services", 
    "INTC": "Technology", "TXN": "Technology", "QCOM": "Technology", "INTU": "Technology", "AMAT": "Technology", 
    "HON": "Industrials", "ISRG": "Healthcare", "SBUX": "Consumer Cyclical", "BKNG": "Consumer Cyclical", 
    "MDLZ": "Consumer Defensive",
    "RELIANCE.NS": "Energy", "TCS.NS": "Technology", "HDFCBANK.NS": "Financial Services", 
    "ICICIBANK.NS": "Financial Services", "INFY.NS": "Technology", "BHARTIARTL.NS": "Communication Services", 
    "SBIN.NS": "Financial Services", "LICI.NS": "Financial Services", "ITC.NS": "Consumer Defensive", 
    "HUL.NS": "Consumer Defensive", "LTIM.NS": "Technology", "BAJFINANCE.NS": "Financial Services", 
    "MARUTI.NS": "Consumer Cyclical", "SUNPHARMA.NS": "Healthcare", "ADANIENT.NS": "Industrials", 
    "ADANIPORTS.NS": "Industrials", "KOTAKBANK.NS": "Financial Services", "TITAN.NS": "Consumer Cyclical", 
    "AXISBANK.NS": "Financial Services", "ASIANPAINT.NS": "Basic Materials", "ULTRACEMCO.NS": "Basic Materials", 
    "NTPC.NS": "Utilities", "TATAMOTORS.NS": "Consumer Cyclical", "M&M.NS": "Consumer Cyclical", 
    "ONGC.NS": "Energy", "POWERGRID.NS": "Utilities", "JSWSTEEL.NS": "Basic Materials", 
    "TATASTEEL.NS": "Basic Materials", "COALINDIA.NS": "Energy", "ADANIPOWER.NS": "Utilities", 
    "TRENT.NS": "Consumer Cyclical", "HAL.NS": "Industrials", "BEL.NS": "Industrials", "ZOMATO.NS": "Consumer Cyclical", 
    "VBL.NS": "Consumer Defensive", "DLF.NS": "Real Estate", "SIEMENS.NS": "Industrials", "GRASIM.NS": "Basic Materials", 
    "HINDALCO.NS": "Basic Materials", "NESTLEIND.NS": "Consumer Defensive", "SBILIFE.NS": "Financial Services", 
    "BAJAJ-AUTO.NS": "Consumer Cyclical", "WIPRO.NS": "Technology", "TECHM.NS": "Technology", 
    "EICHERMOT.NS": "Consumer Cyclical", "INDUSINDBK.NS": "Financial Services", "DIVISLAB.NS": "Healthcare", 
    "BPCL.NS": "Energy", "CIPLA.NS": "Healthcare", "HCLTECH.NS": "Technology", "GAIL.NS": "Energy", 
    "PNB.NS": "Financial Services", "IRFC.NS": "Financial Services", "RECLTD.NS": "Financial Services", 
    "PFC.NS": "Financial Services", "IOC.NS": "Energy", "TATAELXSI.NS": "Technology", "POLYCAB.NS": "Industrials", 
    "CANBK.NS": "Financial Services", "CHOLAFIN.NS": "Financial Services", "SHREECEM.NS": "Basic Materials", 
    "BAJAJHLDNG.NS": "Financial Services", "LODHA.NS": "Real Estate", "TATACOMM.NS": "Communication Services", 
    "JINDALSTEL.NS": "Basic Materials", "AMBUJACEM.NS": "Basic Materials", "ABB.NS": "Industrials", 
    "HAVELLS.NS": "Industrials", "PIDILITIND.NS": "Basic Materials", "TATACONSUM.NS": "Consumer Defensive", 
    "BRITANNIA.NS": "Consumer Defensive", "APOLLOHOSP.NS": "Healthcare", "GODREJCP.NS": "Consumer Defensive", 
    "MAZDOCK.NS": "Industrials", "RVNL.NS": "Industrials", "IRCTC.NS": "Industrials"
}

# --- 2. DATA ENGINES & SAFETY FILTERS ---
def get_safe_last(series, fallback=0.0):
    try:
        if series is None: return float(fallback)
        clean_series = series.dropna()
        if len(clean_series) > 0: return float(clean_series.iloc[-1])
        return float(fallback)
    except Exception:
        return float(fallback)

@st.cache_data(ttl=3600)
def fetch_macro_and_markets():
    macro = yf.download(["^NSEI", "^NDX", "^INDIAVIX", "INR=X"], period="1y", interval="1d")['Close']
    stocks = yf.download(UNIVERSE, period="1y", interval="1d")['Close']
    
    CACHE_FILE = "pe_memory_bank.json"
    pe_memory = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                pe_memory = json.load(f)
        except Exception: pass

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[401, 403, 404, 429, 500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    pe_data = {}
    valid_fetches = 0
    
    for t in UNIVERSE:
        pe_val = np.nan
        try:
            ticker = yf.Ticker(t, session=session)
            info = ticker.info
            val = info.get('trailingPE') or info.get('forwardPE')
            
            if val is not None and not pd.isna(val):
                pe_val = float(val)
                pe_memory[t] = pe_val  
                valid_fetches += 1
            else:
                pe_val = pe_memory.get(t, np.nan) 
                
        except Exception:
            pe_val = pe_memory.get(t, np.nan) 
            
        pe_data[t] = pe_val
        time.sleep(0.1) 
        
    if valid_fetches > 0:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(pe_memory, f)
        except: pass
            
    return macro, stocks, pe_data

def analyze_markets(macro, stock_data_raw, pe_map):
    stocks = stock_data_raw.ffill().bfill()
    
    nifty = macro.get("^NSEI", pd.Series(dtype=float)).dropna()
    ndx = macro.get("^NDX", pd.Series(dtype=float)).dropna()
    vix = macro.get("^INDIAVIX", pd.Series(dtype=float)).dropna()
    usd_inr = macro.get("INR=X", pd.Series(dtype=float)).dropna()
    
    c_nifty = get_safe_last(nifty, 23000.0) 
    dma_200 = get_safe_last(nifty.rolling(200).mean() if len(nifty) > 200 else nifty, c_nifty)
    c_vix = get_safe_last(vix, 15.0)
    c_usd = get_safe_last(usd_inr, 83.50)
    
    macro_status = {
        "Nifty_Trend": "🟢" if c_nifty > dma_200 else "🔴",
        "VIX_Level": "🟢 (Calm)" if c_vix < 15 else ("🟡 (Elevated)" if c_vix < 22 else "🔴 (Panic)"),
        "VIX_Val": c_vix,
        "USD_INR": c_usd,
        "Global_Clear": True if (c_nifty > dma_200) and (c_vix < 22) else False
    }

    m_6m = ((stocks / stocks.shift(126)) - 1).rolling(14).mean()
    vol = (stocks.pct_change().rolling(126).std() * np.sqrt(252)).rolling(14).mean()
    efficiency = m_6m / vol
    
    nifty_base = get_safe_last(nifty.shift(126), c_nifty)
    n_ret = (c_nifty / nifty_base) - 1 if nifty_base != 0 else 0.0
    
    c_ndx = get_safe_last(ndx, 19000.0)
    ndx_base = get_safe_last(ndx.shift(126), c_ndx)
    ndx_ret = (c_ndx / ndx_base) - 1 if ndx_base != 0 else 0.0
    
    raw_list = []
    for t in UNIVERSE:
        try:
            is_us = t in US_STOCKS
            current_price = get_safe_last(stocks.get(t, pd.Series(dtype=float)))
            if current_price == 0.0: continue
            
            high_52w = stocks[t].max()
            low_52w = stocks[t].min()
            
            raw_list.append({
                "Ticker_Full": t,
                "Ticker": t.replace(".NS",""),
                "Country": "US" if is_us else "India",
                "Sector": SECTOR_MAP.get(t, "Unknown"),
                "Momentum": float(get_safe_last(m_6m.get(t, pd.Series(dtype=float))) * 100), 
                "Efficiency": float(get_safe_last(efficiency.get(t, pd.Series(dtype=float)))),
                "Price": current_price,
                "High_52w": high_52w,
                "Low_52w": low_52w,
                "PE Ratio": pe_map.get(t, np.nan),
                "Benchmark_Ret": (ndx_ret if is_us else n_ret) * 100
            })
        except Exception: 
            continue
        
    temp_df = pd.DataFrame(raw_list)
    sector_pe_map = temp_df.groupby('Sector')['PE Ratio'].median().to_dict()

    results = []
    for _, row in temp_df.iterrows():
        sec_pe = sector_pe_map.get(row['Sector'], np.nan)
        
        if pd.notna(row['High_52w']) and pd.notna(row['Low_52w']) and row['High_52w'] != row['Low_52w']:
            pct_52w = float(((row['Price'] - row['Low_52w']) / (row['High_52w'] - row['Low_52w'])) * 100)
        else:
            pct_52w = 100.0
            
        stop_loss = float(row['High_52w'] * 0.85) if pd.notna(row['High_52w']) else 0.0
        
        score = 0
        if row['Momentum'] > row['Benchmark_Ret']: score += 1
        if pd.notna(row['Efficiency']) and row['Efficiency'] > 0.8: score += 1
        if pd.notna(row['PE Ratio']) and pd.notna(sec_pe) and (row['PE Ratio'] < sec_pe): score += 1
        if 40 <= pct_52w <= 96: score += 1
        
        if score == 4: verdict = "💎 ELITE"
        elif score >= 2: verdict = "✅ STABLE"
        else: verdict = "🛑 WEAK"
            
        results.append({
            "Ticker": row['Ticker'],
            "Country": row['Country'],
            "Sector": row['Sector'],
            "Verdict": verdict,
            "Momentum": row['Momentum'],
            "Efficiency": row['Efficiency'],
            "PE Ratio": row['PE Ratio'],
            "Sector PE": sec_pe,
            "Current Price": row['Price'],
            "Stop-Loss Level": stop_loss,
            "52W Percentile": pct_52w,
            "Buffer_Backend": ((row['Price'] - stop_loss) / row['Price']) * 100 if row['Price'] > 0 else 0.0
        })
        
    if results:
        df = pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)
        df.index += 1  
    else:
        df = pd.DataFrame(columns=["Ticker", "Country", "Sector", "Verdict", "Momentum", "Efficiency", "PE Ratio", "Sector PE", "Current Price", "Stop-Loss Level", "52W Percentile", "Buffer_Backend"])
        
    return df, macro_status

# --- 3. UI LAYOUT ---
st.title("🌍 EMI-Shield: Global Master Alpha Cockpit")

with st.expander("📖 DETAILED STRATEGY & TAX-ADJUSTED GOALS", expanded=True):
    st.markdown(f"""
    **Mission:** Completely offset your **{LOAN_APR*100:.2f}% Indian Bank Loan APR** after-tax.
    - **Loan Ledger:** ₹20,20,000 Principle | Monthly EMI: ₹40,573.
    - **Tax Hurdles:** Capital is benchmarked to a **9.54% gross line** to absorb a 20% Short-Term Capital Gains (STCG) tax penalty.
    - **Volatility Shields:** Fresh deployments pause instantly if Nifty breaks below its 200-DMA or India VIX trends above 22.
    """)

macro_data, stock_data, cached_pes = fetch_macro_and_markets()
analysis_df, m_status = analyze_markets(macro_data, stock_data, cached_pes)

st.header("🧭 Global Macro Environment")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Nifty 50 Trend", m_status["Nifty_Trend"])
c2.metric("India VIX (Fear Gauge)", m_status["VIX_Level"], f"{m_status['VIX_Val']:.1f}")
c3.metric("USD / INR Exchange", f"₹{m_status['USD_INR']:.2f}")
if m_status["Global_Clear"]:
    c4.success("🟢 ALL SYSTEMS CLEAR FOR DEPLOYMENT")
else:
    c4.error("🔴 MACRO HAZARD: DEPLOYMENT HALTED")

# --- PERFORMANCE LINE CHART & METRICS ---
st.divider()
st.header("📈 Strategy Returns (Since First EMI: May 4th)")
try:
    ledger = pd.read_csv(SHEET_URL)
    if 'Status' not in ledger.columns: ledger['Status'] = 'Hold'
    if 'Sell Price' not in ledger.columns: ledger['Sell Price'] = 0.0
    
    ledger['Date'] = pd.to_datetime(ledger['Date'], dayfirst=False).dt.tz_localize(None)
    
    macro_data.index = macro_data.index.tz_localize(None)
    stock_data.index = stock_data.index.tz_localize(None)
    
    chart_start_date = pd.to_datetime('2026-05-04')
    dates = macro_data["^NSEI"].dropna().loc[chart_start_date:].index
    
    stock_data_clean = stock_data.reindex(dates).ffill().bfill()
    port_vals = []
    
    for d in dates:
        active = ledger[ledger['Date'] <= d]
        if active.empty:
            port_vals.append(0.0)
            continue
        
        val = 0
        for _, row in active.iterrows():
            ticker = row['Ticker']
            t_mapped = f"{ticker}.NS" if ticker in [t.replace(".NS","") for t in INDIAN_STOCKS] else ticker
            
            is_sold = str(row.get('Status', 'Hold')).strip().lower() == 'sold'
            sell_price = row.get('Sell Price', 0.0)
            
            if is_sold and pd.notna(sell_price) and float(sell_price) > 0:
                val += row['Qty'] * float(sell_price)
            else:
                try: val += row['Qty'] * float(stock_data_clean.loc[d, t_mapped])
                except: val += row['Total_Value']
            
        invested = active['Total_Value'].sum()
        port_returns_pct = ((val / invested) - 1) * 100 if invested > 0 else 0
        port_vals.append(round(port_returns_pct, 2))
        
    nifty_series = macro_data["^NSEI"].loc[chart_start_date:].reindex(dates).ffill().bfill()
    ndx_series = macro_data["^NDX"].loc[chart_start_date:].reindex(dates).ffill().bfill()
    
    nifty_base = nifty_series.iloc[0] if not nifty_series.empty else 1
    ndx_base = ndx_series.iloc[0] if not ndx_series.empty else 1
    
    nifty_pct = (((nifty_series / nifty_base) - 1) * 100).round(2)
    ndx_pct = (((ndx_series / ndx_base) - 1) * 100).round(2)
    hurdle_pct = ((((1 + TAX_ADJUSTED_TARGET)**((dates - chart_start_date).days/365)) - 1) * 100).round(2)
        
    perf = pd.DataFrame({
        "Date": dates, 
        "My Portfolio (%)": port_vals, 
        "Nifty 50 (India) (%)": nifty_pct,
        "NASDAQ 100 (US) (%)": ndx_pct,
        "Tax-Adjusted Hurdle Line (9.54%)": hurdle_pct
    }, index=dates)

    days_elapsed = max(1, (dates[-1] - chart_start_date).days)
    years_elapsed = days_elapsed / 365.25
    
    port_final = perf["My Portfolio (%)"].iloc[-1]
    nifty_final = perf["Nifty 50 (India) (%)"].iloc[-1]
    ndx_final = perf["NASDAQ 100 (US) (%)"].iloc[-1]

    port_ann = (((1 + port_final/100) ** (1/years_elapsed)) - 1) * 100 if port_final > -100 else 0
    nifty_ann = (((1 + nifty_final/100) ** (1/years_elapsed)) - 1) * 100
    ndx_ann = (((1 + ndx_final/100) ** (1/years_elapsed)) - 1) * 100

    m1, m2, m3 = st.columns(3)
    m1.metric("My Portfolio (Since May 4)", f"{port_final:.2f}%", f"{port_ann:.2f}% Annualized")
    m2.metric("Nifty 50 (Since May 4)", f"{nifty_final:.2f}%", f"{nifty_ann:.2f}% Annualized")
    m3.metric("NASDAQ 100 (Since May 4)", f"{ndx_final:.2f}%", f"{ndx_ann:.2f}% Annualized")
    
    fig = px.line(perf, x="Date", y=["My Portfolio (%)", "Nifty 50 (India) (%)", "NASDAQ 100 (US) (%)", "Tax-Adjusted Hurdle Line (9.54%)"],
                  labels={"value": "Return (%)", "variable": "Market Metrics"})
    
    fig.update_traces(line=dict(dash='dash', color='red'), selector=dict(name="Tax-Adjusted Hurdle Line (9.54%)"))
    fig.update_layout(yaxis_title="Return (%)", hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)
    
except Exception as e:
    st.info(f"💡 Waiting for complete ledger data to overlay custom performance plots. Details: {e}")

# --- THE AUDIT & STOP-LOSS ENGINE ---
st.divider()
st.header("♻️ Strategy Portfolio Audit & Stop-Loss Engine")
if st.button("🔍 RUN ACTIVE HOLDINGS AUDIT"):
    try:
        ledger = pd.read_csv(SHEET_URL)
        if 'Status' not in ledger.columns: ledger['Status'] = 'Hold'
        if 'Sell Price' not in ledger.columns: ledger['Sell Price'] = 0.0
            
        audit = ledger.merge(analysis_df, on="Ticker", how="left")
        
        def get_eff_price(r):
            is_sold = str(r.get('Status', 'Hold')).strip().lower() == 'sold'
            if is_sold and pd.notna(r.get('Sell Price')) and float(r.get('Sell Price')) > 0:
                return float(r['Sell Price'])
            return r['Current Price']
            
        audit['Effective Price'] = audit.apply(get_eff_price, axis=1)
        audit['Holding Amount (₹)'] = audit['Qty'] * audit['Effective Price']
        audit['Return (%)'] = ((audit['Effective Price'] - audit['BuyPrice']) / audit['BuyPrice']) * 100
        
        def audit_action(row):
            if str(row.get('Status', 'Hold')).strip().lower() == 'sold': return "💰 CASHED OUT"
            if pd.isna(row['Buffer_Backend']): return "⚠️ GAP DATA"
            if float(row['Buffer_Backend']) <= 0: return "🚨 STOP-LOSS HIT: LIQUIDATE"
            if row['Verdict'] == "🛑 WEAK": return "🛑 RECYCLE ASSETS (SELL)"
            return "💎 UNCONDITIONAL HOLD"
            
        audit['Action'] = audit.apply(audit_action, axis=1)
        
        display_cols = [
            'Ticker', 'Country', 'Status', 'Action', 'Verdict', 'Return (%)', 
            'Holding Amount (₹)', 'Momentum', 'Efficiency', 'PE Ratio'
        ]
        
        st.dataframe(
            audit[display_cols], 
            use_container_width=True,
            column_config={
                "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Holding Amount (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                "Momentum": st.column_config.NumberColumn(format="%.2f%%"), 
                "Efficiency": st.column_config.NumberColumn(format="%.2f"),
                "PE Ratio": st.column_config.NumberColumn(format="%.1f")
            }
        )
        
        to_sell = audit[audit['Action'].str.contains("SELL|LIQUIDATE") & ~audit['Action'].str.contains("CASHED OUT")]
        if not to_sell.empty:
            unique_sells = to_sell['Ticker'].unique().tolist()
            st.error(f"Execution Recommended: Sell out of {', '.join(unique_sells)} entries.")
    except Exception as e: 
        st.error(f"Audit processing failed. Ensure your spreadsheet labels match clean corporate tickers. Error: {e}")

# --- GLOBAL DEPLOYMENT CONTROLLER ---
st.divider()
st.header(f"🎯 Fortnightly Deployment Portal: Fresh ₹{FORTNIGHTLY_SIP:,}")
if st.button("🚀 INITIATE GLOBAL ALPHA MATRIX SCAN"):
    if not m_status["Global_Clear"]:
        st.warning("⚠️ Macro Indicators have breached threshold boundaries. Capital preservation protocol active: hold cash reserves.")
    
    st.subheader("High-Conviction Global Selections")
    elites = analysis_df[analysis_df['Verdict'] == "💎 ELITE"].head(2) 
    cols = st.columns(2)
    
    if elites.empty:
        st.info("ℹ️ No stocks perfectly met the strict 4-Point Strategy criteria today. Look at Stable options below.")
    else:
        for i, (idx, row) in enumerate(elites.iterrows()):
            cols[i].metric(f"{row['Ticker']} ({row['Country']})", f"₹{PER_STOCK_SIP:,}", f"Sector P/E Edge: {row['PE Ratio']:.1f} vs {row['Sector PE']:.1f}")
    
    st.subheader("Complete Multi-Factor Deployment Matrix")
    deploy_df = analysis_df[['Ticker', 'Country', 'Sector', 'Verdict', 'Momentum', 'Efficiency', 'PE Ratio', 'Sector PE', 'Current Price', 'Stop-Loss Level', '52W Percentile']].copy()
    
    def style_deployment_matrix(row):
        styles = [''] * len(row)
        if pd.notna(row['PE Ratio']) and pd.notna(row['Sector PE']) and (row['PE Ratio'] < row['Sector PE']):
            idx = row.index.get_loc('PE Ratio')
            styles[idx] = 'color: #00FF00; font-weight: bold;'
        return styles

    styled_deploy = deploy_df.style.apply(style_deployment_matrix, axis=1)
    
    st.dataframe(
        styled_deploy,
        use_container_width=True,
        height=600,
        column_config={
            "Momentum": st.column_config.ProgressColumn("Momentum", format="%.2f%%", min_value=0, max_value=200),
            "Efficiency": st.column_config.ProgressColumn("Efficiency", format="%.2f", min_value=0, max_value=3),
            "52W Percentile": st.column_config.ProgressColumn("52W Percentile", format="%.1f%%", min_value=0, max_value=100),
            "PE Ratio": st.column_config.NumberColumn(format="%.1f"),
            "Sector PE": st.column_config.NumberColumn(format="%.1f"),
            "Current Price": st.column_config.NumberColumn(format="%.2f"),
            "Stop-Loss Level": st.column_config.NumberColumn(format="%.2f")
        }
    )

# --- THE ORACLE'S VAULT: LONG-TERM VALUE & INSTITUTIONAL TRACKER ---
st.divider()
st.header("🦅 The Oracle's Vault: Long-Term Value & Institutional Tracker")
st.markdown("Shift from high-frequency momentum to long-term compounding based on Warren Buffett's philosophy of economic moats and fair valuations.")

c_buff1, c_buff2 = st.columns(2)

with c_buff1:
    st.subheader("1. The 'Moat & Margin' Screener")
    st.write("Filtering your universe for high-efficiency (moat proxy) and low-valuation (value proxy) assets.")
    
    # Buffett Logic: PE below sector average, PE under 25 (cheap), Efficiency > 1.0 (smooth, consistent compounding)
    buffett_df = analysis_df[
        (analysis_df['PE Ratio'] < analysis_df['Sector PE']) & 
        (analysis_df['PE Ratio'] <= 25) & 
        (analysis_df['Efficiency'] > 1.0)
    ].sort_values("PE Ratio", ascending=True)

    if not buffett_df.empty:
        st.dataframe(
            buffett_df[['Ticker', 'Country', 'Sector', 'PE Ratio', 'Efficiency']], 
            hide_index=True,
            use_container_width=True,
            column_config={
                "PE Ratio": st.column_config.NumberColumn(format="%.1f"),
                "Efficiency": st.column_config.NumberColumn(format="%.2f")
            }
        )
    else:
        st.info("No stocks currently meet the strict deep-value criteria. Holding cash is a valid value position.")

with c_buff2:
    st.subheader("2. Institutional Trade Tracker (Latest Qtr)")
    st.write("Tracking smart money: SEC 13F Filings & NSE Block Deals.")
    
    tab1, tab2 = st.tabs(["🇺🇸 Berkshire Hathaway", "🇮🇳 Parag Parikh Flexi Cap"])
    
    with tab1:
        st.markdown("**Recent Portfolio Action**")
        st.success("🟢 **BUY / INITIATE:** Chubb (CB), Occidental Petroleum (OXY)")
        st.error("🔴 **TRIM / SELL:** Apple (AAPL), Paramount Global (PARA)")
        st.caption("*Source: Latest Proxy SEC 13F Filings*")
        
    with tab2:
        st.markdown("**Recent Portfolio Action**")
        st.success("🟢 **BUY / ADD:** HDFC Bank (HDFCBANK.NS), ITC (ITC.NS)")
        st.error("🔴 **TRIM / SELL:** Wipro (WIPRO.NS)")
        st.caption("*Source: NSE Shareholding Data / Mutual Fund Disclosures*")

# --- LAYMAN'S FINANCE EXPANDED DICTIONARY ---
st.divider()
st.header("📚 The Investor's Dictionary (Layman Edition)")
col_g1, col_g2 = st.columns(2)
with col_g1:
    with st.expander("📈 Annualized Returns vs Absolute Returns", expanded=True):
        st.write("**Absolute Returns:** Exactly how much money you made or lost from May 4th until today, regardless of how much time has passed.")
        st.write("**Annualized Returns (CAGR):** The speed of your money. If your portfolio continued growing at this exact same speed for a full 365 days, this is what the final percentage would be.")
    with st.expander("📈 XIRR (Extended Internal Rate of Return)"):
        st.write("**Full Form:** Extended Internal Rate of Return.")
        st.write("**Plain English:** Your personal investment speedometer.")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("**Full Form:** Relative Price Momentum vs. Benchmarks.")
        st.write("**Plain English:** Pure acceleration. We reject sluggish stocks.")
with col_g2:
    with st.expander("🎯 Efficiency (Sharpe Ratio Score)", expanded=True):
        st.write("**Full Form:** Sharpe Ratio / Risk-Adjusted Return Profiles.")
        st.write("**Plain English:** Ride smoothness. We aggressively prioritize high-efficiency, low-volatility assets to minimize portfolio stress.")
    with st.expander("🛡️ Trailing Stop-Loss Protection"):
        st.write("**Full Form:** Maximum Peak-to-Trough Capital Ceiling Safeguard.")
        st.write("**Plain English:** An automated profit lock acting like an escalator: as your stock climbs to new all-time highs, your floor rises directly behind it.")
    with st.expander("⚖️ 52-Week Price Percentile"):
        st.write("**Plain English:** This metric tells you exactly where a stock's current price sits within its highest and lowest points over the last year. 0% means it is at absolute rock bottom. 100% means it is at an absolute peak. The strategy looks for the 'Goldilocks Zone' (40% to 96%)—meaning the stock is rising but hasn't maxed out its rally.")
