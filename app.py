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

import streamlit as st
import yfinance as yf
import pandas as pd
import datetime as dt

st.set_page_config(page_title="USD Macro Dashboard", layout="wide")

# ============================
# ------- HEADER -------------
# ============================

st.title("💵 USD MACRO DASHBOARD (v1.0)")

st.markdown(
    """
    Tento dashboard vyhodnocuje sílu / slabost amerického dolaru na základě:
    - makro indikátorů (DXY, VIX, US10Y)
    - ručně zadaných fundamentálních reportů (CPI, NFP, ISM, Retail…)
    """
)

# ============================
# --- DATA FETCH -------------
# ============================

@st.cache_data(ttl=3600)
def load_data():
    end = dt.datetime.now()
    start = end - dt.timedelta(days=120)

    dxy = yf.download("DX-Y.NYB", start=start, end=end)
    vix = yf.download("^VIX", start=start, end=end)
    us10y = yf.download("^TNX", start=start, end=end)

    return dxy, vix, us10y

dxy, vix, us10y = load_data()

# ============================
# --- INDICATOR SCORES -------
# ============================

macro_score = 0

# DXY > 100 = +1
latest_dxy = dxy['Close'].iloc[-1]
if latest_dxy > 100:
    macro_score += 1

# VIX < 15 = +1
latest_vix = vix['Close'].iloc[-1]
if latest_vix < 15:
    macro_score += 1

# US10Y > 4% (TNX ukazuje 10Y yield * 10)
latest_10y = us10y['Close'].iloc[-1] / 10
if latest_10y > 0.04:
    macro_score += 1

# ============================
# --- USER FUNDAMENT INPUT ---
# ============================

st.subheader("📝 Fundamentální reporty (ruční zadání)")

reports = ["CPI", "Core CPI", "NFP", "Unemployment", "ISM Manufacturing", "ISM Services", "Retail Sales"]

weights = {
    "Strong Bullish": 1,
    "Slight Bullish": 0.5,
    "Neutral": 0,
    "Slight Bearish": -0.5,
    "Strong Bearish": -1
}

fundamental_score = 0

cols = st.columns(3)

for i, rep in enumerate(reports):
    with cols[i % 3]:
        val = st.selectbox(f"{rep}", list(weights.keys()), index=2)
        fundamental_score += weights[val]

total_score = macro_score + fundamental_score

# ============================
# --- SENTIMENT BOX ----------
# ============================

st.subheader("📊 USD Fundamentální Sentiment")

if total_score >= 2:
    sentiment = "BULLISH USD"
    color = "#00c400"
elif total_score <= -2:
    sentiment = "BEARISH USD"
    color = "#ff3030"
else:
    sentiment = "NEUTRAL USD"
    color = "#d0d0d0"

st.markdown(
    f"""
    <div style="
        background-color:{color};
        padding:25px;
        border-radius:10px;
        text-align:center;
        font-size:28px;
        font-weight:700;">
        {sentiment} (score: {total_score:.1f})
    </div>
    """,
    unsafe_allow_html=True
)

# ============================
# --- CHARTS -----------------
# ============================

st.subheader("📈 DXY — 1D Line Chart")
st.line_chart(dxy["Close"])

st.subheader("📉 VIX — 1D Line Chart")
st.line_chart(vix["Close"])

# ============================
# --- DETAILS BOX ------------
# ============================

st.subheader("📚 Detaily výpočtu")

st.write(f"**📌 DXY:** {latest_dxy:.2f}")
st.write(f"**📌 VIX:** {latest_vix:.2f}")
st.write(f"**📌 10Y Yield:** {latest_10y*100:.2f}%")
st.write(f"**📌 Makro Score:** {macro_score}")
st.write(f"**📌 Fundament Score:** {fundamental_score}")
st.write(f"**📌 TOTAL SCORE:** {total_score:.2f}")


# FOOTER
st.write("---")
st.caption("Dashboard v.1.2 — Clean Professional Theme")
