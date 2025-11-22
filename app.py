import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime


# ======================================================
# ===============  PAGE CONFIG  =========================
# ======================================================

st.set_page_config(
    page_title="USD Dashboard PRO",
    layout="wide"
)

st.title("💵 USD Macro Dashboard – Professional Version")



# ======================================================
# ===============  MODULE A – FUNDAMENTY  ===============
# ======================================================

def fetch_econoday_high_impact():
    url = (
        "https://ec.forexprostools.com/?"
        "action=calendar&"
        "economicCalendarUrl=calendar&"
        "importance=3&"
        "countries=5&"
        "timeZone=15&"
        "lang=1"
    )

    try:
        r = requests.get(url, timeout=10)
        data = r.json()
    except:
        return pd.DataFrame()

    rows = []
    for event in data:
        try:
            date_str = event.get("date")
            time_str = event.get("time", "00:00")

            if date_str:
                dt = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %H:%M")
                date = dt.strftime("%Y-%m-%d")
            else:
                date = None

            actual_raw = event.get("actual")
            forecast_raw = event.get("forecast")
            previous_raw = event.get("previous")

            def to_float(v):
                if v in [None, "", "-", " "]:
                    return None
                try:
                    return float(str(v).replace("%", "").replace(",", ""))
                except:
                    return None

            actual = to_float(actual_raw)
            forecast = to_float(forecast_raw)
            previous = to_float(previous_raw)

            if actual is not None and forecast is not None:
                signal = 1 if actual > forecast else -1 if actual < forecast else 0
            else:
                signal = 0

            rows.append({
                "Date": date,
                "Report": event.get("event"),
                "Actual": actual_raw,
                "Forecast": forecast_raw,
                "Previous": previous_raw,
                "Signal": signal
            })

        except:
            continue

    return pd.DataFrame(rows)



# ======= DISPLAY FUNDAMENT SECTION =======

st.header("📰 USD Makro Fundamenty — High Impact (EconoDay Feed)")

fund = fetch_econoday_high_impact()

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

    total = fund["Signal"].sum()
    st.subheader(f"📊 Celkové USD fundamentální skóre: **{total}**")



# ======================================================
# ===============  MODULE B – DXY & VIX ================
# ======================================================

def fetch_close(symbol):
    try:
        data = yf.Ticker(symbol).history(period="6mo")
        return data
    except:
        return pd.DataFrame()


st.header("📊 DXY & VIX – Daily Charts")

col1, col2 = st.columns(2)

with col1:
    dxy = fetch_close("DX-Y.NYB")
    if not dxy.empty:
        fig = px.line(dxy, y="Close", title="💵 DXY – Daily Close")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("DXY data unavailable.")

with col2:
    vix = fetch_close("^VIX")
    if not vix.empty:
        fig = px.line(vix, y="Close", title="⚠️ VIX – Daily Close")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("VIX data unavailable.")



# ======================================================
# ===============  MODULE C – SEASONALITY ===============
# ======================================================

MONTH_MAP = {
    1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
    7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"
}

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def seasonality_monthly(symbol, years=20):
    df = yf.Ticker(symbol).history(period=f"{years}y")
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df.index = pd.to_datetime(df.index)
    df["Year"] = df.index.year
    df["Month"] = df.index.month

    monthly = df["Close"].groupby([df["Year"], df["Month"]]).last().reset_index()
    monthly["Return"] = monthly.groupby("Year")["Close"].pct_change() * 100
    monthly = monthly.dropna()
    monthly["MonthName"] = monthly["Month"].map(MONTH_MAP)

    # 12-month template
    full_months = pd.DataFrame({"Month": list(range(1,13))})
    full_months["MonthName"] = full_months["Month"].map(MONTH_MAP)

    mean_monthly = (
        monthly.groupby("Month")[["Return"]]
        .mean()
        .reset_index()
        .merge(full_months, on="Month", how="right")
        .sort_values("Month")
    )

    return mean_monthly, monthly


def seasonality_heatmap(df):
    hm = df.pivot(index="Year", columns="MonthName", values="Return")
    hm = hm.reindex(columns=MONTH_ORDER)
    return hm


def render_seasonality(symbol, title):
    st.subheader(title)

    mean_month, full_monthly = seasonality_monthly(symbol)

    fig1 = px.line(
        mean_month,
        x="MonthName",
        y="Return",
        category_orders={"MonthName": MONTH_ORDER},
        markers=True,
        title=f"{title} – Avg Monthly Seasonality (20Y)"
    )
    st.plotly_chart(fig1, use_container_width=True)

    heat = seasonality_heatmap(full_monthly)
    fig2 = px.imshow(
        heat.T,
        aspect="auto",
        labels=dict(x="Year", y="Month", color="% Return"),
        title=f"{title} – Heatmap (20Y)"
    )
    st.plotly_chart(fig2, use_container_width=True)


# ======= DISPLAY =======
st.header("📈 Seasonality – DXY / Gold / S&P500 (20Y)")

render_seasonality("DX-Y.NYB", "DXY (US Dollar Index)")
render_seasonality("GC=F", "Gold (XAU/USD)")
render_seasonality("^GSPC", "S&P 500 Index")
