# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="USD Fundamental Dashboard")

# --------------------
# Helper functions
# --------------------
@st.cache_data(ttl=60)  # cache for 60s
def fetch_history(ticker, period="60d", interval="1d"):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        df = df[['Close']].rename(columns={'Close': 'price'})
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        st.error(f"Fetch error {ticker}: {e}")
        return pd.DataFrame()

def pct_change_latest(series, days=1):
    if len(series) < days+1: return None
    return (series.iloc[-1] - series.iloc[-(days+1)]) / series.iloc[-(days+1)] * 100

def sma(series, window=50):
    if len(series) < window: return None
    return series.rolling(window).mean().iloc[-1]

# --------------------
# Configuration
# --------------------
TICKERS = {
    "DXY_proxy": "UUP",   # USD proxy ETF
    "US10Y_proxy": "IEF", # 7-10y treasury ETF (proxy)
    "VIX_proxy": "VXX",   # VIX proxy
    "SP500": "SPY",
    "GOLD": "GC=F"
}

# --------------------
# UI - header & inputs
# --------------------
st.title("USD Fundamental Dashboard — Streamlit")
st.markdown("Live fundamental sentiment (no API key required). Data via yfinance. Manual CPI/FedWatch optional.")

col1, col2, col3 = st.columns([1,1,2])
with col1:
    cpi_manual = st.number_input("Manual CPI surprise (bp, optional)", value=float('nan'), format="%.1f")
with col2:
    fedwatch_manual = st.number_input("Manual FedWatch hikeProb (%) (optional)", value=float('nan'), format="%.1f")
with col3:
    refresh = st.button("Refresh now")

# --------------------
# Fetch data
# --------------------
period = "90d"
data = {}
for k,ticker in TICKERS.items():
    df = fetch_history(ticker, period=period)
    data[k] = df

# --------------------
# Compute metrics
# --------------------
metrics = {}
for name, df in data.items():
    if df.empty:
        metrics[name] = {'price': None}
        continue
    price = float(df['price'].iloc[-1])
    pct1 = pct_change_latest(df['price'], days=1)
    pct7 = pct_change_latest(df['price'], days=7)
    sma50 = sma(df['price'], window=50)
    trend = "NEUTRAL"
    if sma50 is not None:
        trend = "UP" if price > sma50 else ("DOWN" if price < sma50 else "NEUTRAL")
    metrics[name] = {
        'price': price,
        'pct1': pct1,
        'pct7': pct7,
        'sma50': sma50,
        'trend': trend,
        'history': df
    }

# --------------------
# Scoring logic (same as Sheets)
# --------------------
score = 0
reasons = []

# DXY: up supports USD
dxy = metrics['DXY_proxy']
if dxy['pct1'] is not None:
    if dxy['pct1'] >= 0.3:
        score += 1; reasons.append(f"DXY +{dxy['pct1']:.2f}% -> supports USD")
    elif dxy['pct1'] <= -0.3:
        score -= 1; reasons.append(f"DXY {dxy['pct1']:.2f}% -> opposes USD")

# US10Y proxy - we interpret IEF price inversely: IEF DOWN -> yields UP -> supports USD
ief = metrics['US10Y_proxy']
if ief['pct1'] is not None:
    # compute approximate bp change from IEF pct (rough heuristic) OR look at price move
    # simple rule: if IEF is DOWN -> yields UP -> support USD
    if ief['trend'] == "DOWN":
        score += 1; reasons.append("IEF trend DOWN -> yields up -> supports USD")
    elif ief['trend'] == "UP":
        score -= 1; reasons.append("IEF trend UP -> yields down -> opposes USD")

# VIX proxy: VXX UP -> risk-off -> supports USD
vxx = metrics['VIX_proxy']
if vxx['pct1'] is not None:
    if vxx['pct1'] >= 3.0:
        score += 1; reasons.append(f"VXX +{vxx['pct1']:.2f}% -> risk-off -> supports USD")
    elif vxx['pct1'] <= -3.0:
        score -= 1; reasons.append(f"VXX {vxx['pct1']:.2f}% -> risk-on -> opposes USD")

# SPY: SPY UP -> risk-on -> opposes USD
spy = metrics['SP500']
if spy['pct1'] is not None:
    if spy['pct1'] >= 0.3:
        score -= 1; reasons.append(f"SPY +{spy['pct1']:.2f}% -> risk-on -> opposes USD")
    elif spy['pct1'] <= -0.3:
        score += 1; reasons.append(f"SPY {spy['pct1']:.2f}% -> risk-off -> supports USD")

# CPI manual
if not np.isnan(cpi_manual):
    if cpi_manual >= 5:
        score += 1; reasons.append(f"CPI surprise +{cpi_manual:.1f} bp -> supports USD")
    elif cpi_manual <= -5:
        score -= 1; reasons.append(f"CPI surprise {cpi_manual:.1f} bp -> opposes USD")

# FedWatch manual
if not np.isnan(fedwatch_manual):
    if fedwatch_manual >= 50:
        score += 1; reasons.append("FedWatch high hike prob -> supports USD")
    elif fedwatch_manual <= 20:
        score -= 1; reasons.append("FedWatch low hike prob -> opposes USD")

# Label
if score >= 3:
    overall = "STRONGLY BULLISH USD"
elif score == 2:
    overall = "BULLISH USD"
elif score == 1 or score == 0:
    overall = "NEUTRAL / MIXED"
elif score == -1 or score == -2:
    overall = "BEARISH USD"
else:
    overall = "STRONGLY BEARISH USD"

# --------------------
# Render dashboard
# --------------------
st.markdown("---")
# top cards
c1, c2, c3, c4, c5 = st.columns(5)
def render_card(col, title, metric):
    if metric['price'] is None:
        col.write(title)
        col.error("No data")
        return
    col.metric(title, f"{metric['price']:.2f}", f"1d {metric['pct1']:.2f}%")
render_card(c1, "DXY (UUP)", dxy)
render_card(c2, "US10Y proxy (IEF)", ief)
render_card(c3, "VIX (VXX)", vxx)
render_card(c4, "S&P500 (SPY)", spy)
render_card(c5, "Gold (GC=F)", metrics['GOLD'])

st.markdown("### USD SENTIMENT: " + overall)
st.write("Score:", score)
if reasons:
    st.write("Reasons:")
    for r in reasons:
        st.write(" - " + r)

# show small charts
st.markdown("---")
st.markdown("### History")
chart_cols = st.columns(2)
with chart_cols[0]:
    st.line_chart(dxy['history']['price'].tail(90), height=250, use_container_width=True)
with chart_cols[1]:
    st.line_chart(ief['history']['price'].tail(90), height=250, use_container_width=True)

st.markdown("---")
st.markdown("### Raw data & export")
raw = pd.DataFrame({
    'symbol': [k for k in TICKERS.keys()],
    'ticker': [v for v in TICKERS.values()],
    'price': [metrics[k]['price'] if metrics[k]['price'] is not None else np.nan for k in TICKERS.keys()],
    'pct1': [metrics[k]['pct1'] if metrics[k]['pct1'] is not None else np.nan for k in TICKERS.keys()]
})
st.dataframe(raw)

# --- Economic Calendar embed (Investing.com widget via iframe) ---
import streamlit.components.v1 as components

st.markdown("### 📅 Economic Calendar (local timezone: Europe/Prague)")

# Investing.com widget iframe (locale=english, timezone parameter isn't official in iframe,
# but we can show user's timezone as info)
st.markdown("**Timezone:** Europe/Prague (CET/CEST) — calendar shows local events. See important releases below.")

# You can use Investing.com embeddable calendar URL — it works as iframe.
# If you prefer TradingEconomics widget, I show both options (uncomment desired).
investing_iframe = """
<iframe src="https://www.investing.com/economic-calendar/streaming-availability" 
        width="100%" height="700" frameborder="0" scrolling="yes"></iframe>
"""

# Alternative: TradingEconomics calendar widget (if you prefer)
tradingeconomics_iframe = """
<iframe src="https://tradingeconomics.com/calendar" width="100%" height="700" frameborder="0" scrolling="yes"></iframe>
"""

# Render the iframe (choose one)
components.html(investing_iframe, height=700)  # show Investing.com
# components.html(tradingeconomics_iframe, height=700)  # or use TradingEconomics

# Quick manual highlights area (empty by default, user can write notes)
st.markdown("**Quick highlights / notes:**")
note = st.text_area("Add important scheduled events for your trading (optional)", height=80)
# footer / instructions
st.markdown("---")
st.markdown("**Notes:** yfinance uses Yahoo data. CPI/FedWatch manual inputs optional. To make public, deploy to Streamlit Cloud and share URL.")
