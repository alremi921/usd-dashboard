import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# ============= STYLE =============
st.set_page_config(page_title="USD Macro Dashboard", layout="wide")

PRIMARY_GREEN = "#2ECC71"
PRIMARY_RED = "#E74C3C"
PRIMARY_BLUE = "#2E86C1"
CARD_BG = "#F4F6F7"
CARD_BORDER = "#D5D8DC"

st.markdown("""
<style>
.big-metric {
    font-size: 48px;
    font-weight: 700;
    padding: 0px;
}
.metric-label {
    font-size: 18px;
    color: #555;
}
.result-box {
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 25px;
}
.card {
    background: #F4F6F7;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #D5D8DC;
}
</style>
""", unsafe_allow_html=True)


# ============= FUNCTIONS =============
def fetch(symbol):
    try:
        data = yf.Ticker(symbol).history(period="5d")
        if data.empty:
            return None
        return data["Close"].iloc[-1]
    except:
        return None

def colorize(value, reverse=False):
    if value is None:
        return "black"
    if not reverse:
        return PRIMARY_GREEN if value > 0 else PRIMARY_RED
    else:
        return PRIMARY_RED if value > 0 else PRIMARY_GREEN


# ============= FETCH MACRO DATA =============
symbols = {
    "DXY (Dollar Index)": "DX-Y.NYB",
    "VIX (Volatility Index)": "^VIX",
    "US10Y (10Y Yield)": "^TNX"
}

data = {}
changes = {}

for name, symbol in symbols.items():
    price_now = fetch(symbol)
    df = yf.Ticker(symbol).history(period="5d")
    if not df.empty:
        change = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0] * 100
    else:
        change = None
    data[name] = price_now
    changes[name] = change


# ============= SCORING =============
score = 0

if changes["DXY (Dollar Index)"] and changes["DXY (Dollar Index)"] > 0:
    score += 1
if changes["VIX (Volatility Index)"] and changes["VIX (Volatility Index)"] < 0:
    score += 1
if changes["US10Y (10Y Yield)"] and changes["US10Y (10Y Yield)"] > 0:
    score += 1

sentiment_map = {
    3: ("STRONGLY BULLISH USD", PRIMARY_GREEN),
    2: ("BULLISH USD", PRIMARY_GREEN),
    1: ("NEUTRAL / SLIGHT BULLISH", PRIMARY_BLUE),
    0: ("NEUTRAL", PRIMARY_BLUE),
    -1: ("BEARISH USD", PRIMARY_RED),
    -2: ("STRONGLY BEARISH USD", PRIMARY_RED)
}

sentiment_text, sentiment_color = sentiment_map.get(score, ("NEUTRAL", PRIMARY_BLUE))

# ============= HEADER =============
st.title("💵 USD Macro Dashboard — Professional Version")
st.write("Čistý, profesionální přehled klíčových makro ukazatelů USA")

# ============= MAIN RESULT =============
st.markdown(
    f"""
    <div class='result-box' style="background:{sentiment_color}15;">
        <div class='metric-label'>Aktuální sentiment USD</div>
        <div class='big-metric' style="color:{sentiment_color};">{sentiment_text}</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============= 3 COLUMNS — clean cards =============
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 DXY — Dollar Index")
    st.metric(
        label="Aktuální hodnota",
        value=f"{data['DXY (Dollar Index)']:.2f}" if data["DXY (Dollar Index)"] else "N/A",
        delta=f"{changes['DXY (Dollar Index)']:.2f}%" if changes["DXY (Dollar Index)"] else "N/A"
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("⚡ VIX — Volatility Index")
    st.metric(
        label="Aktuální hodnota",
        value=f"{data['VIX (Volatility Index)']:.2f}" if data["VIX (Volatility Index)"] else "N/A",
        delta=f"{changes['VIX (Volatility Index)']:.2f}%" if changes["VIX (Volatility Index)"] else "N/A"
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💹 US 10Y Yield")
    st.metric(
        label="Aktuální hodnota",
        value=f"{data['US10Y (10Y Yield)']:.2f}" if data["US10Y (10Y Yield)"] else "N/A",
        delta=f"{changes['US10Y (10Y Yield)']:.2f}%" if changes["US10Y (10Y Yield)"] else "N/A"
    )
    st.markdown("</div>", unsafe_allow_html=True)


# FOOTER
st.write("---")
st.caption("Dashboard v.1.2 — Clean Professional Theme")
