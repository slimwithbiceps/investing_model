import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# --- 1. SETTINGS & LOAN CONSTANTS ---
st.set_page_config(page_title="EMI-Shield Global Cockpit", layout="wide")

LOAN_APR = 0.0763  # 7.63% Indian Bank APR
TAX_RATE = 0.20
TAX_ADJUSTED_TARGET = LOAN_APR / (1 - TAX_RATE)  # 9.54% Gross Target
FORTNIGHTLY_SIP = 20000 
PER_STOCK_SIP = 6667 
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJtykI9lRFLh-z8ZhFIbvALKPJbcrXxqLqg05L6yZ4BsHOdum4m8y_W-jmS4CdNXjTEXPiOM0Bmfl8/pub?gid=0&single=true&output=csv" 

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

# --- 2. DATA ENGINES & SAFETY FILTERS ---
def get_safe_last(series, fallback=0.0):
    return float(series.iloc[-1]) if not series.empty else fallback

@st.cache_data(ttl=86400)
def fetch_macro_and_markets():
    macro = yf.download(["^NSEI", "^NDX", "^INDIAVIX", "INR=X"], period="1y", interval="1d")['Close']
    stocks = yf.download(UNIVERSE, period="1y", interval="1d")['Close']
    
    # Cache structural PE details to keep deployment execution immediate
    pe_data = {}
    for t in UNIVERSE:
        try:
            val = yf.Ticker(t).info.get('trailingPE', None)
            pe_data[t] = float(val) if val else np.nan
        except:
            pe_data[t] = np.nan
    return macro, stocks, pe_data

def analyze_markets(macro, stock_data_raw, pe_map):
    stocks = stock_data_raw.ffill().bfill()
    nifty = macro["^NSEI"].dropna()
    ndx = macro["^NDX"].dropna()
    vix = macro["^INDIAVIX"].dropna()
    usd_inr = macro["INR=X"].dropna()
    
    c_nifty = get_safe_last(nifty)
    dma_200 = get_safe_last(nifty.rolling(200).mean(), c_nifty)
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
    
    n_ret = (c_nifty / get_safe_last(nifty.shift(126), c_nifty)) - 1
    ndx_ret = (get_safe_last(ndx) / get_safe_last(ndx.shift(126), get_safe_last(ndx))) - 1
    
    # Step 1: Gather raw metrics across the board
    raw_list = []
    for t in UNIVERSE:
        try:
            is_us = t in US_STOCKS
            current_price = get_safe_last(stocks[t].dropna())
            if current_price == 0.0: continue
            
            high_52w = stocks[t].max()
            raw_list.append({
                "Ticker_Full": t,
                "Ticker": t.replace(".NS",""),
                "Region": "US" if is_us else "India",
                "Momentum": get_safe_last(m_6m[t].dropna()),
                "Efficiency": get_safe_last(efficiency[t].dropna()),
                "Price": current_price,
                "High_52w": high_52w,
                "PE": pe_map.get(t, np.nan),
                "Benchmark_Ret": ndx_ret if is_us else n_ret
            })
        except: continue
        
    temp_df = pd.DataFrame(raw_list)
    
    # Calculate operational tracking limits relative to current regional peers
    india_pe_median = temp_df[temp_df['Region'] == 'India']['PE'].median()
    us_pe_median = temp_df[temp_df['Region'] == 'US']['PE'].median()
    
    # Fallback bounds if broad scraping limits are encountered
    if pd.isna(india_pe_median): india_pe_median = 26.5
    if pd.isna(us_pe_median): us_pe_median = 33.0

    # Step 2: Map structural alpha classification criteria
    results = []
    for _, row in temp_df.iterrows():
        med_pe = us_pe_median if row['Region'] == 'US' else india_pe_median
        
        # Criteria Calculations
        is_rallying = (row['Momentum'] > row['Benchmark_Ret']) and (row['Momentum'] > 0)
        not_at_peak = row['Price'] < (row['High_52w'] * 0.96)  # Minimum 4% pullback headroom from absolute top
        is_undervalued = pd.notna(row['PE']) and (row['PE'] <= med_pe)
        
        stop_loss = row['High_52w'] * 0.85
        
        if is_rallying and not_at_peak and is_undervalued:
            verdict = "💎 ELITE"
        elif row['Efficiency'] > 0.4:
            verdict = "✅ STABLE"
        else:
            verdict = "🛑 WEAK"
            
        results.append({
            "Ticker": row['Ticker'],
            "Region": row['Region'],
            "Verdict": verdict,
            "Momentum": row['Momentum'],
            "Efficiency": row['Efficiency'],
            "PE Ratio": row['PE'],
            "Stop-Loss Level": stop_loss,
            "Price_Backend": row['Price'],             # Retained safely for background loops
            "Buffer_Backend": ((row['Price'] - stop_loss) / row['Price']) * 100
        })
        
    df = pd.DataFrame(results).sort_values("Efficiency", ascending=False).reset_index(drop=True)
    df.index += 1  
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
            try: 
                val += row['Qty'] * float(stock_data_clean.loc[d, t_mapped])
            except: 
                val += row['Total_Value']
            
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
        audit = ledger.merge(analysis_df, on="Ticker", how="left")
        
        audit['Holding Amount (₹)'] = audit['Qty'] * audit['Price_Backend']
        audit['Return (%)'] = ((audit['Price_Backend'] - audit['BuyPrice']) / audit['BuyPrice']) * 100
        
        def audit_action(row):
            if pd.isna(row['Buffer_Backend']): return "⚠️ GAP DATA"
            if float(row['Buffer_Backend']) <= 0: return "🚨 STOP-LOSS HIT: LIQUIDATE"
            if row['Verdict'] == "🛑 WEAK": return "🛑 RECYCLE ASSETS (SELL)"
            return "💎 UNCONDITIONAL HOLD"
            
        audit['Action'] = audit.apply(audit_action, axis=1)
        
        # Display structures stripped of current pricing exposure
        display_cols = [
            'Ticker', 'Region', 'Action', 'Verdict', 'Return (%)', 
            'Holding Amount (₹)', 'Momentum', 'Efficiency', 'PE Ratio', 'Stop-Loss Level'
        ]
        
        st.dataframe(
            audit[display_cols], 
            use_container_width=True,
            column_config={
                "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Holding Amount (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                "Momentum": st.column_config.NumberColumn(format="%.2f%%"), 
                "Efficiency": st.column_config.NumberColumn(format="%.2f"),
                "PE Ratio": st.column_config.NumberColumn(format="%.1f"),
                "Stop-Loss Level": st.column_config.NumberColumn(format="%.2f")
            }
        )
        
        to_sell = audit[audit['Action'].str.contains("SELL|LIQUIDATE")]
        if not to_sell.empty:
            unique_sells = to_sell['Ticker'].unique().tolist()
            st.error(f"Execution Recommended: Sell out of {', '.join(unique_sells)} entries.")
    except Exception as e: 
        st.error(f"Audit processing failed. Ensure your spreadsheet labels match clean corporate tickers like 'HAL' or 'NVDA'. Error details: {e}")

# --- GLOBAL DEPLOYMENT CONTROLLER ---
st.divider()
st.header(f"🎯 Fortnightly Deployment Portal: Fresh ₹{FORTNIGHTLY_SIP:,}")
if st.button("🚀 INITIATE GLOBAL ALPHA MATRIX SCAN"):
    if not m_status["Global_Clear"]:
        st.warning("⚠️ Macro Indicators have breached threshold boundaries. Capital preservation protocol active: hold cash reserves.")
    
    st.subheader("High-Conviction Global Selections")
    elites = analysis_df[analysis_df['Verdict'] == "💎 ELITE"].head(3)
    cols = st.columns(3)
    
    if elites.empty:
        st.info("ℹ️ No stocks perfectly met the strict 'Pullback + Undervalued' strategy criteria today. Hold dry powder or look at Stable options below.")
    else:
        for i, (idx, row) in enumerate(elites.iterrows()):
            cols[i].metric(f"{row['Ticker']} ({row['Region']})", f"₹{PER_STOCK_SIP:,}", f"P/E: {row['PE Ratio']:.1f}")
    
    st.subheader("Complete Global Universe Metrics Rankings")
    # Clean display frame removing raw execution metrics
    rankings_display = analysis_df[['Ticker', 'Region', 'Verdict', 'Momentum', 'Efficiency', 'PE Ratio', 'Stop-Loss Level']]
    
    st.dataframe(rankings_display, column_config={
        "Momentum": st.column_config.NumberColumn("Momentum (6M Smoothed)", format="%.1f%%"),
        "Efficiency": st.column_config.ProgressColumn("Efficiency (Risk-Adj)", min_value=0, max_value=2, format="%.2f"),
        "PE Ratio": st.column_config.NumberColumn("PE Ratio", format="%.1f"),
        "Stop-Loss Level": st.column_config.NumberColumn("Trailing Stop-Loss Floor", format="%.2f")
    }, use_container_width=True)

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
        st.write("**Plain English:** Your personal investment speedometer. Regular returns assume you put in all your money on day one. Because you drop in ₹20,000 blocks sequentially every fortnight, XIRR dynamically tracks how hard every individual rupee is working based on its specific entry date.")
    with st.expander("🚄 Momentum (Alpha)"):
        st.write("**Full Form:** Relative Price Momentum vs. Benchmarks.")
        st.write("**Plain English:** Pure acceleration. We reject sluggish stocks. This tracks whether a selection is running significantly faster than the baseline market indices (^NSEI for India or ^NDX for the US tech market).")
with col_g2:
    with st.expander("🎯 Efficiency (Sharpe Ratio Score)", expanded=True):
        st.write("**Full Form:** Sharpe Ratio / Risk-Adjusted Return Profiles.")
        st.write("**Plain English:** Ride smoothness. If Stock A and Stock B both return 20%, but Stock A goes up in a calm, steady line while Stock B experiences massive, gut-wrenching daily spikes, Stock A has a much higher Efficiency Score. Because you have a locked-in ₹40,573 auto-debit obligation every month, we aggressively prioritize high-efficiency, low-volatility assets to minimize portfolio stress.")
    with st.expander("🛡️ Trailing Stop-Loss Protection"):
        st.write("**Full Form:** Maximum Peak-to-Trough Capital Ceiling Safeguard.")
        st.write("**Plain English:** An automated profit lock. A standard stop-loss stays fixed forever. A *trailing* stop-loss acts like an escalator: as your stock climbs to new all-time highs, your floor rises directly behind it (anchored exactly 15% below peak price values). If market trends break down, it triggers a liquidate warning to salvage your profits.")
