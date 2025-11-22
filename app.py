import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime

# ======================================================
# PAGE CONFIG
# ======================================================

st.set_page_config(
    page_title="USD Dashboard PRO",
    layout="wide"
)

st.title("💵 USD Macro Dashboard – Professional Version")


# ======================================================
# ============= MODULE A: FUNDAMENTS ===================
# ======================================================

def fetch_usd_macro_events():
    """
    Pulls USD high-impact economic events (forexprostools feed).
    Fully working version with required headers.
    """
    url = (
        "https://ec.forexprostools.com/?"
        "action=calendar&"
        "economicCalendarUrl=calendar&"
        "importance=3&"
        "countries=5&"
        "timeZone=15&"
        "lang=1"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.investing.com/economic-calendar/"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        events = r.json()
    except:
        return pd.DataFrame()

    rows = []

    for ev in events:
        try:
            date = ev.get("date", "")
            time = ev.get("time", "00:00")
            dt = datetime.strptime(f"{date} {time}", "%m/%d/%Y %H:%M")

            def clean(x):
                if x in [None, "-", ""]:
                    return None
                try:
                    return float(str(x).replace("%", "").replace(",", ""))
                except:
                    return None

            actual = clean(ev.get("actual"))
            forecast = clean(ev.get("forecast"))

            # Signal: +1 bullish, 0 neutral, -1 bearish
            signal = 0
            if actual is not None and forecast is not None:
                signal = 1 if actual > forecast else -1 if actual < forecast else 0

            rows.append({
                "Date": dt.strftime("%Y-%m-%d"),
                "Report": ev.get("event"),
                "Actual": ev.get("actual"),
                "Forecast": ev.get("forecast"),
                "Previous": ev.get("previous"),
                "Signal": signal,
            })

        except:
            continue

    df = pd.DataFrame(rows)
    return df


# ======================================================
# DISPLAY FUNDAMENT SECTION
# ======================================================

st.header("📰 USD Makro Fundamenty — High Impact (Realtime)")

fund = fetch_usd_macro_events()

if fund.empty:
    st.warning("⚠️ Nepodařilo se načíst makro data.")
else:
    fund = fund.sort_values("Date", ascending=False)
    fund["Signal Label"] = fund["Signal"].map({
        1: "🔺 +1 Bullish",
        0: "⏺ 0 Neutral",
        -1: "🔻 -1 Bearish"
    })

    st.dataframe(
        fund[["Date", "Report", "Actual", "Forecast", "Previous", "Signal Label"]],
        use_container_width=True
    )

    total_score = fund["Signal"].sum()
    st.subheader(f"📊 Celkové fundamentální skóre: **{total_score}**")

st.markdown("---")



# ======================================================
# ============= MODULE B: DXY & VIX ====================
# ======================================================

def fetch_symbol(symbol):
    try:
        df = yf.Ticker(symbol).history(period="6mo")
        return df
    except:
        return pd.DataFrame()


st.header("📊 DXY & VIX — Daily Charts")

col1, col2 = st.columns(2)

with col1:
    dxy = fetch_symbol("DX-Y.NYB")
    if not dxy.empty:
        fig = px.line(
            dxy,
            y="Close",
            title="💵 DXY — Dollar Index (Daily Close)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("DXY data unavailable.")

with col2:
    vix = fetch_symbol("^VIX")
    if not vix.empty:
        fig = px.line(
            vix,
            y="Close",
            title="⚡ VIX — Volatility Index (Daily Close)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("VIX data unavailable.")

st.markdown("---")



# ======================================================
# ============= MODULE C: SEASONALITY ==================
# ======================================================

MONTH_MAP = {
    1: "Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
    7: "Jul", 8:"Aug", 9:"Sep",10:"Oct",11:"Nov",12:"Dec"
}

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


def seasonality_monthly(symbol, years=20):
    df = yf.Ticker(symbol).history(period=f"{years}y")

    if df.empty:
        return None, None

    df.index = pd.to_datetime(df.index)
    df["Year"] = df.index.year
    df["Month"] = df.index.month

    monthly = (
        df["Close"].groupby([df["Year"], df["Month"]])
        .last()
        .reset_index()
    )

    monthly["Return"] = monthly.groupby("Year")["Close"].pct_change() * 100
    monthly = monthly.dropna()

    monthly["MonthName"] = monthly["Month"].map(MONTH_MAP)

    avg_month = (
        monthly.groupby("Month")["Return"]
        .mean()
        .reindex(range(1,13))
        .reset_index()
    )

    avg_month["MonthName"] = avg_month["Month"].map(MONTH_MAP)

    return avg_month, monthly


def seasonality_heatmap(df):
    hm = df.pivot(index="Year", columns="MonthName", values="Return")
    hm = hm.reindex(columns=MONTH_ORDER)
    return hm


def render_seasonality(symbol, title):
    st.subheader(title)

    avg_month, raw = seasonality_monthly(symbol)

    # Line chart
    fig = px.line(
        avg_month,
        x="MonthName",
        y="Return",
        category_orders={"MonthName": MONTH_ORDER},
        markers=True,
        title=f"{title} — Avg Monthly Seasonality (20Y)"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Heatmap
    heat = seasonality_heatmap(raw)

    fig2 = px.imshow(
        heat.T,
        aspect="auto",
        labels=dict(x="Year", y="Month", color="% Return"),
        title=f"{title} — Heatmap (20Y)"
    )
    st.plotly_chart(fig2, use_container_width=True)



# ======================================================
# DISPLAY SEASONALITY SECTION
# ======================================================

st.header("📈 Seasonality — DXY / Gold / S&P 500 (20Y)")

render_seasonality("DX=F", "DXY (Dollar Index Futures)")
render_seasonality("GC=F", "Gold (XAU/USD)")
render_seasonality("^GSPC", "S&P 500 Index")
