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
# ============= MODULE A: FUNDAMENTS (NO ICALENDAR) ====
# ======================================================

def fetch_usd_macro_events():
    """
    FairEconomy JSON feed – 100% funkční, bez potřeby knihovny icalendar.
    """
    url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"

    try:
        data = requests.get(url, timeout=10).json()
    except:
        return pd.DataFrame()

    rows = []

    for ev in data.get("data", []):
        # Filter USD + High impact
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
        previous = ev.get("previous")

        def clean(x):
            if x in [None, "", "-"]: 
                return None
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
            "Previous": previous,
            "Signal": signal
        })

    df = pd.DataFrame(rows)
    return df


# ======================================================
# ============= DISPLAY FUNDAMENT SECTION ==============
# ======================================================

st.header("📰 USD Makro Fundamenty — High Impact (Realtime)")

fund = fetch_usd_macro_events()

if fund.empty:
    st.warning("⚠️ Nepodařilo se načíst makro data.")
else:
    fund["Date"] = pd.to_datetime(fund["Date"])
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

    # ==========================================
    # AI SHRUTÍ FUNDAMENTŮ (lokální generátor)
    # ==========================================
    def ai_summarize_macro(df):
        bullish = df[df["Signal"] == 1].shape[0]
        bearish = df[df["Signal"] == -1].shape[0]
        neutral = df[df["Signal"] == 0].shape[0]
        last = df.iloc[0]["Report"]

        tone = "bullish" if total_score > 0 else "bearish" if total_score < 0 else "neutral"

        summary = f"""
### 🤖 AI Shrnutí USD Fundamentů

V posledních dnech byly publikovány klíčové americké makroekonomické indikátory.
Celkový stav fundamentů pro USD je aktuálně **{tone.upper()}**.

- Počet pozitivních překvapení: **{bullish}**
- Počet negativních výsledků: **{bearish}**
- Neutrální výsledky: **{neutral}**
- Poslední publikovaný report: **{last}**

Na základě celkového fundamentálního skóre **({total_score})** lze očekávat, že USD bude 
v krátkodobém horizontu mít **{tone} momentum**, pokud nedojde k výrazné změně v nadcházejících datech.
"""
        return summary

    st.markdown(ai_summarize_macro(fund))

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
            dxy, y="Close",
            title="💵 DXY — Dollar Index (Daily Close)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("DXY data unavailable.")

with col2:
    vix = fetch_symbol("^VIX")
    if not vix.empty:
        fig = px.line(
            vix, y="Close",
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
    1: "Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May",
    6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep",
    10:"Oct", 11:"Nov", 12:"Dec"
}

MONTH_ORDER = list(MONTH_MAP.values())


def seasonality_monthly(symbol, years=20):
    df = yf.Ticker(symbol).history(period=f"{years}y")

    if df.empty:
        return None, None

    df.index = pd.to_datetime(df.index)
    df["Year"] = df.index.year
    df["Month"] = df.index.month

    # monthly close
    monthly = df.groupby([df["Year"], df["Month"]])["Close"].last().reset_index()

    # month-to-month % change
    monthly["Return"] = monthly.groupby("Year")["Close"].pct_change() * 100
    monthly = monthly.dropna()

    monthly["MonthName"] = monthly["Month"].map(MONTH_MAP)

    avg_month = (
        monthly.groupby("Month")["Return"]
        .mean()
        .reindex(range(1, 13))
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
        avg_month, x="MonthName", y="Return",
        markers=True,
        category_orders={"MonthName": MONTH_ORDER},
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
