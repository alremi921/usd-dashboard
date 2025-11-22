# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import os 

st.set_page_config(page_title="USD Macro AI Dashboard", layout="wide")
st.title("💵 USD Macro AI Dashboard — Category Scoring (Manuálně zadaná data)")

# -------------------------
# CONFIGURACE
# -------------------------
# Cesta k vašemu manuálně spravovanému souboru s příponou .txt
CSV_FILE_PATH = "usd_macro_history.csv.txt" 
LOOKBACK_DAYS = 90  # 3 měsíce pro filtrování zobrazení
TODAY = datetime.utcnow()
START_DATE = TODAY - timedelta(days=LOOKBACK_DAYS)

# KEYWORDS (pouze pro definici kategorií v tabulkách)
CATEGORY_KEYWORDS = {
    "Inflace": [], "Úrokové sazby": [], "Trh práce": [], "Ekonomická aktivita": []
}

# Pomocná funkce: čištění číselných polí (odstranění %, K, M, B)
def clean_num(x):
    if x is None: return None
    s = str(x).strip()
    if s.startswith('.'): s = s[1:]
    if s == "" or s == "-" or s.lower() == "n/a" or s.lower() == "nan": return None
    s = s.replace("%", "").replace(",", "").replace("K", "000").replace("M", "000000").replace("B", "000000000")
    try: return float(s)
    except: return None

# Načtení dat z lokálního CSV
def load_events_from_csv():
    if not os.path.exists(CSV_FILE_PATH):
        st.error(f"Chyba: Soubor s daty '{CSV_FILE_PATH}' nebyl nalezen. Vytvořte jej prosím dle šablony.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(CSV_FILE_PATH)
        
        # Kontrola povinných sloupců
        required_cols = ['Date', 'Category', 'Actual', 'Forecast', 'Report']
        if not all(col in df.columns for col in required_cols):
             st.error(f"Chyba: V CSV chybí jeden z povinných sloupců: {required_cols}")
             return pd.DataFrame()

        df["DateParsed"] = pd.to_datetime(df["Date"], errors="coerce")
        
        # Filtr: Zobrazit data stará max 3 měsíce
        df = df[df["DateParsed"].notna()]
        df = df[df["DateParsed"] >= pd.Timestamp(START_DATE)]
        
        return df.sort_values("DateParsed", ascending=False).reset_index(drop=True)
    
    except Exception as e:
        st.error(f"Nepodařilo se načíst nebo zpracovat soubor CSV. Zkontrolujte formátování. Chyba: {e}")
        return pd.DataFrame()

# Skórování události: porovnání Actual vs Forecast -> +1 / -1 / 0
def score_event(row):
    a = clean_num(row.get("Actual"))
    f = clean_num(row.get("Forecast"))
    
    if a is None or f is None: return 0 # Skóre je 0, pokud Actual nebo Forecast chybí
    if a > f: return 1
    if a < f: return -1
    return 0

# Vyhodnocení kategorie
def evaluate_category(df_cat):
    total = int(df_cat["Points"].sum())
    if total > 2: label = "Bullish"
    elif total < -2: label = "Bearish"
    else: label = "Neutral"
    return total, label

# AI shrnutí
def generate_ai_summary(summary_df, final_score, overall_label):
    summary = f"Celkové fundamentální skóre pro USD za poslední 3 měsíce (manuálně zadaná data) je **{final_score:+d}**, což vyúsťuje v **{overall_label}** sentiment. "
    
    sorted_summary = summary_df.sort_values("Total Points", ascending=False)
    
    # Detaily
    if not sorted_summary.empty:
        best_cat = sorted_summary.iloc[0]
        if best_cat['Total Points'] > 0:
            summary += f"Nejsilnější pozitivní vliv na USD má kategorie **{best_cat['Category']}** s výsledkem **{best_cat['Total Points']:+d} bodů** ({best_cat['Events Count']} událostí). "
        
        worst_cat = sorted_summary.iloc[-1]
        if worst_cat['Total Points'] < 0:
            summary += f"Negativně působí kategorie **{worst_cat['Category']}** se skóre **{worst_cat['Total Points']:+d} bodů** ({worst_cat['Events Count']} událostí). "
    
    if overall_label == "Bullish pro USD":
        summary += "Fundamentální býčí sentiment je tažen silnými daty, která převážila mírně negativní zprávy. "
    elif overall_label == "Bearish pro USD":
        summary += "Celková medvědí nálada je způsobena kumulací slabších výsledků. "
    else: summary += "Celkový neutralní výsledek poukazuje na vyváženou situaci. "
    return summary

# -------------------------
# BUILD DASHBOARD
# -------------------------
st.header("Data fetch & processing")
with st.spinner(f"Načítám data z lokálního souboru '{CSV_FILE_PATH}' (posledních ~{LOOKBACK_DAYS} dní)..."):
    df_high = load_events_from_csv()

if df_high.empty:
    st.error("Nepodařilo se načíst žádná platná data. Zkontrolujte 'usd_macro_history.csv.txt'.")
    st.stop()

# Výpočet bodů a příprava k zobrazení
df_high["Points"] = df_high.apply(score_event, axis=1)
df_high["DateDisplay"] = df_high["DateParsed"].dt.strftime("%Y-%m-%d %H:%M")

st.success(f"Načteno {len(df_high)} událostí v rámci sledovaného období.")
st.markdown("---")

# -------------------------
# Tabulky podle témat
# -------------------------
st.header("Tabulky podle témat")
cols = st.columns(2)

category_frames = {}
unique_categories = df_high["Category"].unique() 

for i, cat in enumerate(unique_categories):
    cat_df = df_high[df_high["Category"] == cat].copy()
    if cat_df.empty: continue 
    
    cat_df = cat_df.sort_values("DateParsed", ascending=False)
    display_df = cat_df[["DateDisplay", "Report", "Actual", "Forecast", "Previous", "Points"]].rename(
        columns={"DateDisplay":"Date","Report":"Report","Actual":"Actual","Forecast":"Forecast","Previous":"Previous","Points":"Points"}
    )
    category_frames[cat] = cat_df

    if i % 2 == 0:
        with cols[0]:
            st.subheader(cat)
            st.dataframe(display_df, use_container_width=True)
    else:
        with cols[1]:
            st.subheader(cat)
            st.dataframe(display_df, use_container_width=True)

st.markdown("---")

# -------------------------
# Agregace a finální vyhodnocení
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
final_score = int(summary_df["Total Points"].sum())
if final_score > 2: overall_label = "Bullish pro USD"
elif final_score < -2: overall_label = "Bearish pro USD"
else: overall_label = "Neutral pro USD"

st.subheader("Category summary")
st.table(summary_df.style.format({"Total Points":"{:+d}"}))
st.markdown(f"### 🔎 Celkové fundamentální skóre: **{final_score:+d}** — **{overall_label}**")

# AI Vyhodnocení
st.markdown("---")
st.header("🤖 AI Fundamentální Vyhodnocení")
ai_text = generate_ai_summary(summary_df, final_score, overall_label)
st.info(ai_text)

# Vizualizace
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
    
# Export
st.markdown("---")
st.header("Export / download")

csv_all = df_high.sort_values("DateParsed", ascending=False)[
    ["DateDisplay","Category","Report","Actual","Forecast","Previous","Points"]
].rename(columns={"DateDisplay":"Date"})
st.download_button("Download events CSV", csv_all.to_csv(index=False).encode("utf-8"), "usd_macro_events_manual.csv", "text/csv")