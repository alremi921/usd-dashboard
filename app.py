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
# ============================================================
# USD FUNDAMENTY — EconDB API (funguje bez API klíče)
# ============================================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta


ECONDB_SERIES = {
    "NFP": "NFP",
    "CPI YoY": "CPIAUCSL",
    "Core CPI YoY": "CPILFESL",
    "PPI YoY": "PPIACO",
    "ISM Manufacturing PMI": "NAPM",
    "Unemployment Rate": "UNRATE",
    "Initial Jobless Claims": "ICSA"
}


def fetch_econdb_series(series_code):
    """
    Returns latest 3 observations of a macro series from EconDB.
    """
    url = f"https://www.econdb.com/api/series/{series_code}/?format=json"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
    except:
        return None

    try:
        df = pd.DataFrame({
            "date": data["dates"],
            "value": data["values"]
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False)
        return df.head(3)
    except:
        return None


def build_usd_macro_table():
    rows = []

    for label, series in ECONDB_SERIES.items():
        df = fetch_econdb_series(series)
        if df is None or len(df) < 2:
            continue

        actual = df.iloc[0]["value"]
        previous = df.iloc[1]["value"]
        date = df.iloc[0]["date"].strftime("%Y-%m-%d")

        # Forecast bohužel EconDB neobsahuje → simulujeme forecast = previous
        forecast = previous

        if actual > forecast:
            signal = 1
        elif actual < forecast:
            signal = -1
        else:
            signal = 0

        rows.append({
            "Date": date,
            "Report": label,
            "Actual": actual,
            "Forecast": forecast,
            "Previous": previous,
            "Signal": signal
        })

    return pd.DataFrame(rows)


# ==== STREAMLIT VÝSTUP ====

st.header("📰 USD Makro Fundamenty — poslední data (EconDB)")

fund = build_usd_macro_table()

if fund.empty:
    st.warning("⚠️ Nepodařilo se načíst makro data z EconDB.")
else:
    def sig_label(v):
        if v > 0: return "🔺 +1"
        if v < 0: return "🔻 -1"
        return "⏺ 0"

    fund["Signal Label"] = fund["Signal"].apply(sig_label)

    st.dataframe(
        fund[["Date", "Report", "Actual", "Forecast", "Previous", "Signal Label"]],
        use_container_width=True
    )

    total_score = fund["Signal"].sum()
    st.subheader(f"📊 Celkové USD Fundamentální Skóre: **{total_score}**")
# ============================================================
# SEASONALITY — monthly line chart + heatmap (20 let)
# ============================================================
import yfinance as yf
import pandas as pd
import plotly.express as px
import streamlit as st


def seasonality_monthly(symbol, years=20):
    df = yf.Ticker(symbol).history(period=f"{years}y")
    if df.empty:
        return pd.DataFrame()

    df.index = pd.to_datetime(df.index)
    df["Year"] = df.index.year
    df["Month"] = df.index.month

    monthly = df["Close"].groupby([df["Year"], df["Month"]]).last().reset_index()
    monthly["Return"] = monthly.groupby("Year")["Close"].pct_change() * 100
    monthly = monthly.dropna()

    monthly["MonthName"] = monthly["Month"].map({
        1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
        7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
    })

    # 20 yr average
    mean_monthly = (
        monthly.groupby("Month")[["Return"]]
        .mean()
        .reset_index()
        .sort_values("Month")
    )
    mean_monthly["MonthName"] = mean_monthly["Month"].map({
        1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
        7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
    })
    return mean_monthly, monthly


def seasonality_heatmap(monthly_df):
    pivot = monthly_df.pivot(index="Year", columns="MonthName", values="Return")
    pivot = pivot.fillna(0)
    return pivot


def render_seasonality(symbol, title):
    st.subheader(title)

    mean_monthly, monthly_full = seasonality_monthly(symbol)

    # Line chart
    fig_line = px.line(
        mean_monthly,
        x="MonthName",
        y="Return",
        markers=True,
        title=f"{title} — Average Monthly Seasonality (20Y)",
        labels={"Return": "% Avg Return"}
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # Heatmap
    heat = seasonality_heatmap(monthly_full)
    fig_hm = px.imshow(
        heat.T,
        aspect="auto",
        labels=dict(x="Year", y="Month", color="% Return"),
        title=f"{title} — Heatmap (20Y)"
    )
    st.plotly_chart(fig_hm, use_container_width=True)


# ===== DISPLAY =====
st.header("📈 Seasonality — DXY / Gold / S&P500")

render_seasonality("DX-Y.NYB", "DXY (Dollar Index)")
render_seasonality("GC=F", "Gold (XAU/USD)")
render_seasonality("^GSPC", "S&P 500 (SPX)")

# FOOTER
st.caption("Dashboard v.2.0 — Base version (bez fundamentů)")
