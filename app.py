# --- Economic Calendar embed (Investing.com widget via iframe) ---
import streamlit.components.v1 as components

st.markdown("### 📅 Economic Calendar (local timezone: Europe/Prague)")

# Investing.com widget iframe (locale=english, timezone parameter isn't official in iframe,
# but we can show user's timezone as info)
st.markdown("**Timezone:** Europe/Prague (CET/CEST) — calendar shows local events. See important releases below.")

# You can use Investing.com embeddable calendar URL — it works as iframe.
# If you prefer TradingEconomics widget, I show both options (uncomment desired).
investing_iframe = """
<iframe src="https://www.investing.com/economic-calendar/streaming-availability" 
        width="100%" height="700" frameborder="0" scrolling="yes"></iframe>
"""

# Alternative: TradingEconomics calendar widget (if you prefer)
tradingeconomics_iframe = """
<iframe src="https://tradingeconomics.com/calendar" width="100%" height="700" frameborder="0" scrolling="yes"></iframe>
"""

# Render the iframe (choose one)
components.html(investing_iframe, height=700)  # show Investing.com
# components.html(tradingeconomics_iframe, height=700)  # or use TradingEconomics

# Quick manual highlights area (empty by default, user can write notes)
st.markdown("**Quick highlights / notes:**")
note = st.text_area("Add important scheduled events for your trading (optional)", height=80)
