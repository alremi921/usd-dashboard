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
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import requests
from datetime import datetime, timedelta


# =====================================================
# 1️⃣   EconDB API – HIGH IMPACT USD NEWS (last 30 days)
# =====================================================

def fetch_usd_high_impact_last_month():
    """
    Fetches last 30 days of USD macroeconomic high-impact reports
    using EconDB API (stable, reliable, JSON-based).
    """

    # List of major high-impact USD indicators
    high_impact_series = {
        "NFP": "NFP",
        "CPI": "CPI",
        "Core CPI": "CPIC",
        "PCE": "PCEPI",
        "Core PCE": "PCEPI_CORE",
        "Retail Sales": "RS",
        "ISM Manufacturing PMI": "ISM_MAN",
        "ISM Services PMI": "ISM_SERV",
        "Unemployment Rate": "UNRATE",
        "GDP QoQ": "GDP_USA"
    }

    end = datetime.utcnow()
    start = end - timedelta(days=30)

    all_rows = []

    for name, series_code in high_impact_series.items():
        url = f"https://www.econdb.com/api/series/{series_code}/?format=json"
        r = requests.get(url)
        if r.status_code != 200:
            continue

        data = r.json()

        dates = data["data"]["dates"]
        values = data["data"]["values"]

        # Build dataframe
        df = pd.DataFrame({"Date": dates, "Actual": values})
        df["Date"] = pd.to_datetime(df["Date"])

        # Filter last 30 days
        df = df[df["Date"].between(start, end)]

        if df.empty:
            continue

        # Create signals (we need forecast from EconDB → proxy: compare to previous)
        df = df.sort_values("Date")
        df["Forecast"] = df["Actual"].shift(1)
        df = df.dropna()

        # Signal = actual vs forecast
        df["Signal"] = df.apply(
            lambda row: 1 if row["Actual"] > row["Forecast"]
            else -1 if row["Actual"] < row["Forecast"]
            else 0,
            axis=1
        )

        df["Report"] = name

        all_rows.append(df)

    if not all_rows:
        return pd.DataFrame()

    final = pd.concat(all_rows, ignore_index=True)
    final["Date"] = final["Date"].dt.strftime("%Y-%m-%d")
    final = final.sort_values("Date", ascending=False)

    return final[["Date", "Report", "Actual", "Forecast", "Signal"]]


# =====================================================
# 2️⃣   SEASONALITY (unchanged)
# =====================================================

def get_seasonality():
    df = yf.Ticker("DX-Y.NYB").history(period="20y")
    df["Month"] = df.index.month
    df["Return"] = df["Close"].pct_change()

    out = df.groupby("Month")["Return"].mean().reset_index()
    out["Return"] = out["Return"] * 100

    out["Month"] = out["Month"].map({
        1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
        7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
    })

    return out


# =====================================================
# 3️⃣ STREAMLIT SECTION
# =====================================================

st.header("📰 USD High-Impact Fundamenty — Posledních 30 dní (EconDB)")

cal = fetch_usd_high_impact_last_month()

if cal.empty:
    st.warning("⚠️ Za posledních 30 dní nejsou žádná dostupná high-impact USD data.")
else:
    st.dataframe(cal, use_container_width=True)
    total_score = cal["Signal"].sum()
    st.subheader(f"📊 Celkové fundamentální skóre (30 dní): **{total_score}**")



# SEASONALITY SECTION
st.header("📈 USD Seasonality — 20 Year Pattern")

season = get_seasonality()
fig = px.bar(
    season,
    x="Month",
    y="Return",
    title="DXY Seasonality (% průměrný měsíční výnos, 20 let)",
    color="Return",
    color_continuous_scale="Bluered"
)
st.plotly_chart(fig, use_container_width=True)

# FOOTER
st.caption("Dashboard v.2.0 — Base version (bez fundamentů)")
