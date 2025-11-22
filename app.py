# app.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="USD Macro AI Dashboard", layout="wide")
st.title("💵 USD Macro AI Dashboard — Category Scoring (last 6 months)")

# -------------------------
# CONFIG
# -------------------------
# how far back (days)
LOOKBACK_DAYS = 180  # ~6 months
TODAY = datetime.utcnow()
START_DATE = TODAY - timedelta(days=LOOKBACK_DAYS)

# endpoints to try (robust)
JSON_WEEK_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
JSON_CDN = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"
XML_WEEK_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
XML_CDN = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml"

# KEYWORDS for categories (case-insensitive)
CATEGORY_KEYWORDS = {
    "Inflace": [
        "cpi", "core cpi", "pce", "core pce", "consumer price", "inflation"
    ],
    "Úrokové sazby": [
        "fomc", "fed rate", "dot plot", "federal funds", "interest rate",
        "federal open market", "fed statement", "fed policy", "press conference", "fed speakers"
    ],
    "Trh práce": [
        "nonfarm payroll", "nfp", "unemployment rate", "jolts", "job openings",
        "average hourly", "hourly earnings", "initial jobless", "continuing claims"
    ],
    "Ekonomická aktivita": [
        "pmi", "ism", "retail sales", "gdp", "gross domestic product", "industrial production", "manufacturing", "services pmi"
    ]
}

# helper: map category by title
def categorize_title(title):
    t = title.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                return cat
    return None

# helper: clean numeric fields -> float or None
def clean_num(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s == "-" or s.lower() == "n/a":
        return None
    # remove % and commas
    s = s.replace("%", "").replace(",", "")
    try:
        return float(s)
    except:
        return None

# Try to fetch weekly JSON (current week) — also will be used as fallback multiple times
def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

# Fetch XML and parse events
def fetch_xml(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.text
    except Exception:
        return None
    return None

# Parse JSON structure returned by ff_calendar_thisweek.json
def parse_faireconomy_json(json_data):
    rows = []
    if not json_data:
        return rows
    # data may be under 'data' or be a list
    data_list = json_data.get("data") if isinstance(json_data, dict) else json_data
    if data_list is None:
        return rows
    for ev in data_list:
        try:
            # typical fields: country, impact (1-3), event, timestamp, actual, forecast, previous
            country = ev.get("country")
            impact = ev.get("impact", 0)
            event = ev.get("event") or ev.get("title") or ev.get("summary") or ""
            ts = ev.get("timestamp")  # unix timestamp (seconds)
            if ts:
                dt = datetime.utcfromtimestamp(int(ts))
                dt_str = dt.strftime("%Y-%m-%d %H:%M")
            else:
                dt_str = None
            rows.append({
                "Date": dt_str,
                "Country": country,
                "Impact": impact,
                "Report": event,
                "Actual": ev.get("actual"),
                "Forecast": ev.get("forecast"),
                "Previous": ev.get("previous")
            })
        except Exception:
            continue
    return rows

# Parse XML (ff_calendar_thisweek.xml format)
def parse_faireconomy_xml(xml_text):
    rows = []
    if not xml_text:
        return rows
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return rows
    # xml structure: <event> elements
    for event in root.findall(".//event"):
        try:
            title = event.findtext("title") or ""
            country = event.findtext("country")
            impact_text = event.findtext("impact")
            impact = None
            if impact_text:
                # some xml uses 'High' / 'Medium' or numeric. Try to coerce.
                try:
                    impact = int(impact_text)
                except:
                    impact = {"Low":1,"Medium":2,"High":3}.get(impact_text.strip(), 0)
            # date/time - try <date> or <timestamp> or <time> tags
            date_text = event.findtext("date") or event.findtext("time") or event.findtext("date_time")
            # sometimes <time> is like "2025-11-22 14:30:00"
            dt_str = None
            if date_text:
                try:
                    dt = pd.to_datetime(date_text)
                    dt_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    dt_str = date_text
            # sometimes xml contains <timestamp> with unix seconds
            ts_node = event.findtext("timestamp")
            if not dt_str and ts_node:
                try:
                    dt = datetime.utcfromtimestamp(int(ts_node))
                    dt_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    dt_str = None
            forecast = event.findtext("forecast")
            actual = event.findtext("actual")
            previous = event.findtext("previous")
            # append
            rows.append({
                "Date": dt_str,
                "Country": country,
                "Impact": int(impact) if impact is not None else 0,
                "Report": title,
                "Actual": actual,
                "Forecast": forecast,
                "Previous": previous
            })
        except Exception:
            continue
    return rows

# Collect events from multiple sources for the last 6 months (weekly crawl)
def collect_events_6mo():
    all_rows = []

    # 1) Try the canonical JSON endpoint for current & near weeks
    for url in (JSON_CDN, JSON_WEEK_URL):
        j = fetch_json(url)
        if j:
            rows = parse_faireconomy_json(j)
            all_rows.extend(rows)

    # 2) Try XML weekly endpoint (it usually contains many events; we will try date parameters monthly as fallback)
    for url in (XML_CDN, XML_WEEK_URL):
        xml_text = fetch_xml(url)
        if xml_text:
            rows = parse_faireconomy_xml(xml_text)
            all_rows.extend(rows)

    # 3) As a robust attempt: iterate backward weekly and try to fetch weekly JSON by passing date param (many installations support ?date=YYYY-MM-DD)
    # We'll attempt for up to 26 weeks
    weeks = 26
    for w in range(weeks):
        target = TODAY - timedelta(weeks=w)
        # try a few URL templates (some servers accept ?date=YYYY-MM-DD or ?date=M.YYYY)
        templates = [
            f"https://nfs.faireconomy.media/ff_calendar_thisweek.json?date={target.strftime('%Y-%m-%d')}",
            f"https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json?date={target.strftime('%Y-%m-%d')}",
            f"https://nfs.faireconomy.media/ff_calendar_thisweek.xml?date={target.strftime('%m.%Y')}",
            f"https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml?date={target.strftime('%m.%Y')}"
        ]
        got_any = False
        for t in templates:
            # small optimization: skip JSON templates if we already have many items
            try:
                if t.endswith(".json") or ".json?" in t:
                    j = fetch_json(t)
                    if j:
                        rows = parse_faireconomy_json(j)
                        if rows:
                            all_rows.extend(rows)
                            got_any = True
                else:
                    xml_text = fetch_xml(t)
                    if xml_text:
                        rows = parse_faireconomy_xml(xml_text)
                        if rows:
                            all_rows.extend(rows)
                            got_any = True
            except Exception:
                continue
        # optional: break if we gather plenty (not necessary)
    # deduplicate by Report + Date
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
    # normalize Date to datetime when possible
    df["DateParsed"] = pd.to_datetime(df["Date"], errors="coerce")
    # only keep within lookback window
    df = df[df["DateParsed"].notna()]
    df = df[df["DateParsed"] >= pd.Timestamp(START_DATE)]
    df = df.sort_values("DateParsed", ascending=False)
    df = df.drop_duplicates(subset=["Report", "DateParsed"], keep="first").reset_index(drop=True)
    return df

# Score each event: compare actual vs forecast -> +1 / -1 / 0
def score_event(row):
    a = clean_num(row.get("Actual"))
    f = clean_num(row.get("Forecast"))
    if a is None or f is None:
        return 0  # neutral if missing data
    if a > f:
        return 1
    if a < f:
        return -1
    return 0

# AI-style evaluator (simple rule-based aggregator requested)
def evaluate_category(df_cat):
    # sum points
    total = int(df_cat["Points"].sum())
    # return classification per user's rule:
    # >2 bullish, 1/0/-1 neutral, <-2 bearish -> but user text said: "a teď >2=bullish pro dolar, 1,0,-1=neutrální pro dolar, <-2=bearish pro dolar"
    # Map:
    if total > 2:
        label = "Bullish"
    elif total < -2:
        label = "Bearish"
    else:
        label = "Neutral"
    return total, label

# -------------------------
# BUILD DASHBOARD
# -------------------------
st.header("Data fetch & processing")
with st.spinner("Stahuji a zpracovávám ekonomické události (posledních ~6 měsíců)..."):
    df_all = collect_events_6mo()

if df_all.empty:
    st.error("Nepodařilo se stáhnout žádné události z ekonomického kalendáře. Zkus znovu nebo zkontroluj konektivitu.")
    st.stop()

# Keep only high impact (impact >=3) OR try to include high impact synonyms
# Some feeds use 3 for high, some use 'High' etc. We will filter by Impact>=3 OR 'impact' text contains 'High' in raw Report (already filtered by feed in many cases)
df_all["ImpactNum"] = pd.to_numeric(df_all["Impact"], errors="coerce").fillna(0).astype(int)
# If ImpactNum is 0 but title contains 'high', treat as 3
df_all.loc[(df_all["ImpactNum"] == 0) & (df_all["Report"].str.lower().str.contains("high")), "ImpactNum"] = 3
df_high = df_all[df_all["ImpactNum"] >= 3].copy()

# Add Category
df_high["Category"] = df_high["Report"].apply(lambda r: categorize_title(str(r)) )
# Keep only events that matched one of our categories
df_high = df_high[df_high["Category"].notna()].copy()

# Compute Points
df_high["Points"] = df_high.apply(score_event, axis=1)

# Standardize date string for display
df_high["DateDisplay"] = df_high["DateParsed"].dt.strftime("%Y-%m-%d %H:%M")

# Show counts
st.success(f"Nalezeno {len(df_high)} high-impact událostí v cílových kategoriích za posledních {LOOKBACK_DAYS} dní.")

# -------------------------
# Create per-category tables
# -------------------------
st.header("Tabulky podle témat")
cols = st.columns(2)

category_frames = {}
for cat in CATEGORY_KEYWORDS.keys():
    cat_df = df_high[df_high["Category"] == cat].copy()
    # sort by date desc
    cat_df = cat_df.sort_values("DateParsed", ascending=False)
    # display minimal columns
    display_df = cat_df[["DateDisplay", "Report", "Actual", "Forecast", "Previous", "Points"]].rename(
        columns={"DateDisplay":"Date","Report":"Report","Actual":"Actual","Forecast":"Forecast","Previous":"Previous","Points":"Points"}
    )
    category_frames[cat] = cat_df  # keep original for aggregation

    # place in UI: 2 columns, alternating
    if list(CATEGORY_KEYWORDS.keys()).index(cat) % 2 == 0:
        with cols[0]:
            st.subheader(cat)
            st.dataframe(display_df, use_container_width=True)
    else:
        with cols[1]:
            st.subheader(cat)
            st.dataframe(display_df, use_container_width=True)

st.markdown("---")

# -------------------------
# Aggregation & final evaluation
# -------------------------
st.header("Souhrn: agregace bodů + celkové vyhodnocení fundamentu")

summary_rows = []
for cat, df_cat in category_frames.items():
    total, label = evaluate_category(df_cat)
    summary_rows.append({
        "Category": cat,
        "Events Count": int(len(df_cat)),
        "Total Points": total,
        "Evaluation": label
    })

summary_df = pd.DataFrame(summary_rows)

# calculate final combined score: sum of category totals
final_score = int(summary_df["Total Points"].sum())
# overall label by user's rule (>2 bullish, <-2 bearish, else neutral)
if final_score > 2:
    overall_label = "Bullish pro USD"
elif final_score < -2:
    overall_label = "Bearish pro USD"
else:
    overall_label = "Neutral pro USD"

# show category summary
st.subheader("Category summary")
st.table(summary_df.style.format({"Total Points":"{:+d}"}))

# final row
st.markdown(f"### 🔎 Celkové fundamentální skóre: **{final_score:+d}** — **{overall_label}**")

# -------------------------
# Optional: timeline & viz
# -------------------------
st.markdown("---")
st.header("Vizualizace: body v čase (timeline)")

viz_df = df_high.copy()
viz_df["DateSimple"] = viz_df["DateParsed"].dt.date
viz_agg = viz_df.groupby(["DateSimple","Category"])["Points"].sum().reset_index()

if not viz_agg.empty:
    fig = px.line(viz_agg, x="DateSimple", y="Points", color="Category", markers=True,
                  title="Body podle kategorie v čase (denní agregát)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Není dost dat pro graf.")

# -------------------------
# Allow CSV export
# -------------------------
st.markdown("---")
st.header("Export / download")
st.markdown("Stáhni data pro další analýzu:")

# full events CSV
csv_all = df_high.sort_values("DateParsed", ascending=False)[
    ["DateDisplay","Category","Report","Actual","Forecast","Previous","Points"]
].rename(columns={"DateDisplay":"Date"})
st.download_button("Download events CSV", csv_all.to_csv(index=False).encode("utf-8"), "usd_macro_events_6mo.csv", "text/csv")

# summary CSV
st.download_button("Download summary CSV", summary_df.to_csv(index=False).encode("utf-8"), "usd_macro_summary.csv", "text/csv")

st.success("Hotovo — dashboard vytvořen. Pokud chceš, můžu:")
st.write("- přidat váhy pro jednotlivé kategorie (např. inflace = 2x),")
st.write("- změnit pravidla pro přiřazení slov do kategorií, nebo")
st.write("- přidat detailní AI-popis pro každou kategorii (styl GPT).")
