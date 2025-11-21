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

