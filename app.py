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
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh


# ============================================================
# 🔄  AUTO REFRESH (každých 90 minut)
# ============================================================

st_autorefresh(interval=90 * 60 * 1000, key="datarefresh")


# ============================================================
# 1️⃣ FUNDAMENTY – FMP Economic Calendar (all USD reports)
# ============================================================

API_KEY = "demo"

def fetch_usd_reports_last_month():
    end = datetime.utcnow()
    start = end - timedelta(days=30)

    url = (
        f"https://financialmodelingprep.com/api/v3/economic_calendar"
        f"?from={start.strftime('%Y-%m-%d')}"
        f"&to={end.strftime('%Y-%m-%d')}"
        f"&apikey={API_KEY}"
    )

    r = requests.get(url)
    if r.status_code != 200:
        return pd.DataFrame()

    events = r.json()
    rows = []

    for e in events:
        if (
            e.get("country") == "US"
            and e.get("actual") is not None
            and e.get("estimate") is not None
        ):
            actual = e["actual"]
            forecast = e["estimate"]

            # sentiment
            if actual > forecast:
                signal = 1
            elif actual < forecast:
                signal = -1
            else:
                signal = 0

            rows.append({
                "Date": e.get("date", "")[:10],
                "Report": e.get("event", ""),
                "Actual": actual,
                "Forecast": forecast,
                "Previous": e.get("previous", None),
                "Signal": signal
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values("Date", ascending=False)
    return df


# ============================================================
# 2️⃣ SEASONALITY FUNCTION – DXY, GOLD, SP500
# ============================================================

def get_seasonality(symbol, years=20):
    df = yf.Ticker(symbol).history(period=f"{years}y")

    if df.empty:
        return pd.DataFrame()

    df["Month"] = df.index.month
    df["Return"] = df["Close"].pct_change()

    s = df.groupby("Month")["Return"].mean().reset_index()
    s["Return"] = s["Return"] * 100

    s["Month"] = s["Month"].map({
        1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
        7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
    })

    return s


# ============================================================
# STREAMLIT SECTION – FUNDAMENTÁLNÍ PŘEHLED
# ============================================================

st.header("📰 USD Makro Fundamenty — Posledních 30 dní")

cal = fetch_usd_reports_last_month()

if cal.empty:
    st.warning("⚠️ Žádná makro data za posledních 30 dní nejsou k dispozici.")
else:
    st.dataframe(
        cal,
        use_container_width=True,
        column_config={
            "Signal": st.column_config.NumberColumn(
                "Signal",
                help="+1 bullish, 0 neutral, -1 bearish",
                format="%d"
            )
        }
    )
    score = cal["Signal"].sum()
    st.subheader(f"📊 Celkové fundamentální skóre: **{score}**")


# ============================================================
# STREAMLIT – SEASONALITY (DXY, GOLD, SP500)
# ============================================================

st.header("📈 USD, Gold & S&P 500 Seasonality (20 let)")


# --- DXY ---
dxy = get_seasonality("DX-Y.NYB")
fig_dxy = px.bar(
    dxy, x="Month", y="Return",
    title="DXY Seasonality (20 let)",
    color="Return",
    color_continuous_scale="Bluered"
)
st.plotly_chart(fig_dxy, use_container_width=True)


# --- GOLD (XAUUSD) ---
gold = get_seasonality("GC=F")
fig_gold = px.bar(
    gold, x="Month", y="Return",
    title="Gold Seasonality (20 let)",
    color="Return",
    color_continuous_scale="Sunset"
)
st.plotly_chart(fig_gold, use_container_width=True)


# --- S&P 500 ---
spx = get_seasonality("^GSPC")
fig_spx = px.bar(
    spx, x="Month", y="Return",
    title="S&P 500 Seasonality (20 let)",
    color="Return",
    color_continuous_scale="Viridis"
)
st.plotly_chart(fig_spx, use_container_width=True)


# FOOTER
st.caption("Dashboard v.2.0 — Base version (bez fundamentů)")
