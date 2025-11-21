import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import requests
from bs4 import BeautifulSoup
import plotly.express as px

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
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)


# ============= FUNCTIONS =============
def fetch_history(symbol, days="1y"):
    df = yf.Ticker(symbol).history(period=days)
    return df


def fetch_last_price(symbol):
    try:
        return yf.Ticker(symbol).history(period="5d")["Close"].iloc[-1]
    except:
        return None


# ForexFactory scraping
def fetch_forex_factory():
    url = "https://www.forexfactory.com/calendar"
    page = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(page.text, "html.parser")

    rows = soup.select("tr.calendar_row")

    events = []
    for r in rows:
        impact = r.get("data-impact")
        if impact not in ["High", "Medium"]:  
            continue

        title = r.get("data-event")
        currency = r.get("data-symbol")
        actual = r.get("data-actual")
        forecast = r.get("data-forecast")

        if currency != "USD":
            continue

        if actual and forecast:
            try:
                a = float(actual.replace(",", ""))
                f = float(forecast.replace(",", ""))
                delta = a - f
            except:
                delta = None
        else:
            delta = None

        events.append({
            "title": title,
            "actual": actual,
            "forecast": forecast,
            "impact": impact,
            "delta": delta
        })

    return pd.DataFrame(events)


def score_fundamentals(df):
    score = 0
    for _, row in df.iterrows():
        if row["delta"] is None:
            continue

        # > forecast bullish USD
        if row["delta"] > 0:
            score += 1
        else:
            score -= 1

    return score


# ============= FETCH DATA =============
dxy_df = fetch_history("DX-Y.NYB")
vix_df = fetch_history("^VIX")

dxy_price = fetch_last_price("DX-Y.NYB")
vix_price = fetch_last_price("^VIX")

forex_df = fetch_forex_factory()
fx_score = score_fundamentals(forex_df)

# ============= COMBINED SENTIMENT =============
total_score = fx_score
sentiment = "NEUTRAL"
sentiment_color = PRIMARY_BLUE

if total_score > 2:
    sentiment = "BULLISH USD"
    sentiment_color = PRIMARY_GREEN
elif total_score < -2:
    sentiment = "BEARISH USD"
    sentiment_color = PRIMARY_RED

# ============= HEADER =============
st.title("💵 USD Macro Dashboard — Professional Version")
st.write("Realtime makro fundamenty + DXY a VIX grafy + sentiment USD")

# ============= MAIN RESULT =============
st.markdown(
    f"""
    <div class='result-box' style="background:{sentiment_color}15;">
        <div class='metric-label'>Celkový USD sentiment</div>
        <div class='big-metric' style="color:{sentiment_color};">{sentiment}</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============= METRICS =============
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📊 DXY — Dollar Index")
    st.metric("Aktuální hodnota", f"{dxy_price:.2f}")
    st.plotly_chart(px.line(dxy_df, y="Close", title="DXY — Daily Line Chart"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("⚡ VIX — Volatility Index")
    st.metric("Aktuální hodnota", f"{vix_price:.2f}")
    st.plotly_chart(px.line(vix_df, y="Close", title="VIX — Daily Line Chart"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ============= FUNDAMENTALS TABLE =============
st.subheader("📰 Realtime Fundamentální Zprávy (ForexFactory)")

st.dataframe(forex_df)

st.write(f"### Celkové fundamentální skóre: **{fx_score}**")

# FOOTER
st.write("---")
st.caption("Dashboard v.2.0 — Realtime Macro Engine Enhanced")
