import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px

# --- SETTINGS & BENCHMARKS (APRIL 2026) ---
st.set_page_config(page_title="EMI-Shield Pro", layout="wide")
NIFTY_PE = 21.4
NIFTY_MOMENTUM = 0.021  # 2.1% 1-year return
NIFTY_VOL = 0.18        # 18% Annualized volatility

# REPLACE with your Google Sheet CSV Link (File > Share > Publish to Web > CSV)
SHEET_URL = "YOUR_LINK_HERE"

def get_detailed_rankings(tickers):
    data = yf.download(tickers, period="1y", interval="1wk")['Close']
    returns = (data.iloc[-1] / data.iloc[-52]) - 1
    vol = data.pct_change().std() * np.sqrt(52)
    
    results = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            pe = info.get('trailingPE', 0)
            
            # SCORING LOGIC
            score = (returns[t] / vol[t])
            
            # REASONING & VERDICT
            if returns[t] > NIFTY_MOMENTUM and pe < NIFTY_PE * 1.5 and vol[t] < 0.30:
                verdict = "💎 STRONG ACCUMULATE"
                reason = "Beating Nifty Momentum with reasonable valuation."
            elif returns[t] > 0 and pe < NIFTY_PE * 2:
                verdict = "✋ HOLD"
                reason = "Trend is positive but valuation is getting rich."
            else:
                verdict = "⚠️ TRIM / AVOID"
                reason = "Underperforming benchmark or extreme volatility."
            
            results.append({
                'Ticker': t,
                'Verdict': verdict,
                'Momentum vs Nifty': f"{((returns[t] - NIFTY_MOMENTUM)*100):.1f}%",
                'P/E Ratio': round(pe, 1),
                'Efficiency (Risk-Adj)': round(score, 2),
                'Instruction': reason
            })
        except: continue
    
    return pd.DataFrame(results).sort_values('Efficiency (Risk-Adj)', ascending=False).reset_index(drop=True)

# --- UI LAYOUT ---
st.title("🛰️ EMI-Shield: Pro Command Center")

# 1. MARKET BENCHMARKS
st.subheader("📊 Market Context (Nifty 50 Benchmarks)")
m1, m2, m3 = st.columns(3)
m1.metric("Nifty P/E", NIFTY_PE, "Target: < 22")
m2.metric("Nifty 1Y Return", f"{NIFTY_MOMENTUM*100}%", "Market is flat/choppy")
m3.metric("Nifty Volatility", f"{NIFTY_VOL*100}%", "Risk Floor")

# 2. SIP HISTORY (From Google Sheets)
st.divider()
st.subheader("📈 Your SIP History & Allocation")
try:
    df_history = pd.read_csv(SHEET_URL)
    # Grouping by Ticker to show total invested
    sip_summary = df_history.groupby('Ticker')['Total_Value'].sum().reset_index()
    fig = px.bar(sip_summary, x='Ticker', y='Total_Value', title="Cumulative Investment per Stock")
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("💡 Connect your Google Sheet to see your SIP History chart here.")

# 3. ANALYSIS & INSTRUCTIONS
st.divider()
st.subheader("🎯 This Fortnight's Strategy Analysis")

if st.button("Run Deep Scan"):
    universe = ["HAL.NS", "BEL.NS", "TRENT.NS", "ZOMATO.NS", "RELIANCE.NS", "TCS.NS", "ITC.NS", "BHARTIARTL.NS"]
    analysis = get_detailed_rankings(universe)
    
    # EXACT INSTRUCTIONS BOX
    st.warning("⚡ EXACT ACTIONS FOR YOUR ₹45,000:")
    top_buys = analysis[analysis['Verdict'] == "💎 STRONG ACCUMULATE"].head(3)
    
    if not top_buys.empty:
        for idx, row in top_buys.iterrows():
            st.write(f"- **Invest ₹15,000 into {row['Ticker']}**: {row['Instruction']}")
    else:
        st.write("- **Hold Cash**: No stocks currently meet the 'Strong Accumulate' benchmark. Park ₹45k in a Liquid Fund.")

    st.table(analysis)
