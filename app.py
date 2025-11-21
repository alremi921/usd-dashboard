import streamlit as st
import yfinance as yf
import pandas as pd
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


# ============= FETCH FUNCTIONS =============
def fetch_history(symbol, period="1y"):
    return yf.Ticker(symbol).history(period=period)


def fetch_last_price(symbol):
    df = yf.Ticker(symbol).history(period="5d")
    if df.empty:
        return None
    return df["Close"].iloc[-1]


# ============= LOAD DATA =============
dxy_df = fetch_history("DX-Y.NYB")
vix_df = fetch_history("^VIX")

dxy_price = fetch_last_price("DX-Y.NYB")
vix_price = fetch_last_price("^VIX")

# ============= MAIN HEADER =============
st.title("💵 USD Macro Dashboard — Professional Version")
st.write("Realtime makro přehled + grafy DXY a VIX")


# ============= SENTIMENT PLACEHOLDER (FUNDAMENTS WILL FEED THIS) =============
sentiment = "NEUTRAL"
sentiment_color = PRIMARY_BLUE

st.markdown(
    f"""
    <div class='result-box' style="background:{sentiment_color}15;">
        <div class='metric-label'>Celkový USD sentiment</div>
        <div class='big-metric' style="color:{sentiment_color};">{sentiment}</div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============= DXY + VIX CARDS =============
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


# ========= PLACE FOR FUNDAMENTS + SEASONALITY =========
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta


# =====================================================
# 1️⃣   USD HIGH-IMPACT NEWS — LAST 30 DAYS
# =====================================================
def fetch_usd_high_impact_last_month():
    url = "https://www.investing.com/economic-calendar/"
    headers = {"User-Agent": "Mozilla/5.0"}

    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.text, "html.parser")

    rows = soup.select("tr.js-event-item")

    dataset = []
    today = datetime.utcnow()
    month_ago = today - timedelta(days=30)

    for row in rows:
        try:
            currency = row.get("data-event-currency")
            impact = row.get("data-impact")     # 3 = high impact
            time_str = row.get("data-release-time")  # timestamp
            title = row.get("data-event-title")
            actual = row.get("data-event-actual")
            forecast = row.get("data-event-forecast")

            # Only USD, only high impact
            if currency != "USD" or impact != "3":
                continue

            # Check valid date
            if not time_str:
                continue
            timestamp = int(time_str)
            date = datetime.utcfromtimestamp(timestamp)

            if date < month_ago:
                continue

            # Skip non-numeric data
            if not actual or not forecast or actual == "-" or forecast == "-":
                continue

            # convert strings → float
            def to_float(x):
                return float(x.replace(",", "").replace("%", ""))

            a = to_float(actual)
            f = to_float(forecast)

            # scoring
            if a > f:
                signal = 1
            elif a < f:
                signal = -1
            else:
                signal = 0

            dataset.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Report": title,
                "Actual": actual,
                "Forecast": forecast,
                "Signal": signal
            })
        except:
            continue

    df = pd.DataFrame(dataset)
    df = df.sort_values("Date", ascending=False)
    return df


# =====================================================
# 2️⃣   SEASONALITY — DXY last 20 years
# =====================================================
def get_seasonality():
    df = yf.Ticker("DX-Y.NYB").history(period="20y")
    df["Month"] = df.index.month
    df["Return"] = df["Close"].pct_change()

    out = df.groupby("Month")["Return"].mean().reset_index()
    out["Return"] = out["Return"] * 100  # convert to %

    out["Month"] = out["Month"].map({
        1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
        7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
    })

    return out


# =====================================================
# 3️⃣ STREAMLIT SECTION — DISPLAY
# =====================================================

# -------- FUNDAMENTS TABLE ----------
st.header("📰 USD High-Impact Fundamenty — Posledních 30 dní")

cal = fetch_usd_high_impact_last_month()

if cal.empty:
    st.warning("⚠️ Za poslední měsíc nejsou dostupné žádné USD high-impact reporty.")
else:
    st.dataframe(cal, use_container_width=True)

    # Total sentiment
    total_score = cal["Signal"].sum()
    st.subheader(f"📊 Celkové fundamentální skóre (30 dní): **{total_score}**")


# -------- SEASONALITY ----------
st.header("📈 USD Seasonality — 20 Year Pattern")

season = get_seasonality()
fig = px.bar(
    season,
    x="Month",
    y="Return",
    title="DXY Seasonality (% průměrná měsíční výkonnost, 20 let)",
    color="Return",
    color_continuous_scale="Bluered"
)
st.plotly_chart(fig, use_container_width=True)


# FOOTER
st.caption("Dashboard v.2.0 — Base version (bez fundamentů)")
