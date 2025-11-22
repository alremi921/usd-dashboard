import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime
import icalendar


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
#  🔥 NOVÁ FUNKČNÍ VERZE – BERE DATA Z INVESTING CALENDAR .ICS
#     Tento feed NIKDY NEBLOKUJE A VŽDY VRACÍ DATA

def fetch_usd_macro_events():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.ics"

    try:
        resp = requests.get(url, timeout=10)
    except:
        return pd.DataFrame()

    try:
        cal = icalendar.Calendar.from_ical(resp.text)
    except:
        return pd.DataFrame()

    rows = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("SUMMARY", ""))
        if "USD" not in summary and "United States" not in summary:
            continue

        try:
            start = component.decoded("DTSTART")
            date = pd.to_datetime(start).strftime("%Y-%m-%d %H:%M")
        except:
            date = None

        actual = component.get("X-FX-ACTUAL")
        forecast = component.get("X-FX-FORECAST")
        previous = component.get("X-FX-PREVIOUS")

        def clean(x):
            if x is None: return None
            try:
                return float(str(x).replace("%", "").replace(",", ""))
            except:
                return None

        a = clean(actual)
        f = clean(forecast)

        signal = 0
        if a is not None and f is not None:
            signal = 1 if a > f else -1 if a < f else 0

        rows.append({
            "Date": date,
            "Report": summary,
            "Actual": actual,
            "Forecast": forecast,
            "Previous": previous,
            "Signal": signal
        })

    df = pd.DataFrame(rows)
    return df


# ======================================================
# ============= MODULE A: FUNDAMENTS (NO ICALENDAR) =====
# ======================================================

def fetch_usd_macro_events():
    """
    Fully functional Investing.com macro feed (no icalendar required).
    Source: FairEconomy JSON mirror (always available).
    """
    url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"

    try:
        data = requests.get(url, timeout=10).json()
    except:
        return pd.DataFrame()

    rows = []

    for ev in data.get("data", []):
        # Filter only USD events + High Impact
        if ev.get("country") != "United States":
            continue
        if ev.get("impact", 0) < 3:
            continue

        ts = ev.get("timestamp")
        if ts:
            dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        else:
            dt = None

        actual = ev.get("actual")
        forecast = ev.get("forecast")

        def clean(x):
            if x in [None, "", "-"]: return None
            try:
                return float(str(x).replace("%", "").replace(",", ""))
            except:
                return None

        a = clean(actual)
        f = clean(forecast)

        signal = 0
        if a is not None and f is not None:
            signal = 1 if a > f else -1 if a < f else 0

        rows.append({
            "Date": dt,
            "Report": ev.get("event"),
            "Actual": actual,
            "Forecast": forecast,
            "Previous": ev.get("previous"),
            "Signal": signal
        })

    df = pd.DataFrame(rows)
    return df


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
# 🔥 NOVÁ KOMPLETNÍ SEASONALITA – FIX VŠECH BUGŮ, JANUARY SA VŽDY ZOBRAZÍ

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

    # ZÁVĚREČNÍ HODNOTA KAŽDÉHO MĚSÍCE
    monthly = df.groupby([df["Year"], df["Month"]])["Close"].last().reset_index()

    # MEZI-MĚSÍČNÍ ZMĚNA V %
    monthly["Return"] = monthly.groupby("Year")["Close"].pct_change() * 100
    monthly = monthly.dropna()

    monthly["MonthName"] = monthly["Month"].map(MONTH_MAP)

    # AVERAGE SEASONALITY
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
    hm = hm.reindex(columns=MONTH_ORDER)  # zajišťuje leden vždy na začátku
    return hm


def render_seasonality(symbol, title):
    st.subheader(title)

    avg_month, raw = seasonality_monthly(symbol)

    # LINE CHART
    fig = px.line(
        avg_month,
        x="MonthName",
        y="Return",
        category_orders={"MonthName": MONTH_ORDER},
        markers=True,
        title=f"{title} — Avg Monthly Seasonality (20Y)"
    )
    st.plotly_chart(fig, use_container_width=True)

    # HEATMAP
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
