import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import pandas as pd
import pytz
import plotly.express as px
from streamlit_js_eval import streamlit_js_eval

# Page Configuration
st.set_page_config(page_title="Rank Analytics Pro", layout="wide")

# Custom CSS for high-visibility
st.markdown("""
    <style>
    table { width: 100% !important; border-collapse: collapse; margin-bottom: 20px; }
    td { padding: 12px; border-bottom: 1px solid #eee; font-size: 16px; font-weight: bold; }
    th { background-color: #f0f2f6; padding: 10px; text-align: left; }
    .stMetric { background-color: #f8f9fb; padding: 15px; border-radius: 10px; box-shadow: 0px 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# Auto-Timezone Detection
browser_tz_name = streamlit_js_eval(js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone", key="tz_eval")
user_tz = pytz.timezone(browser_tz_name) if browser_tz_name else pytz.utc

if 'history' not in st.session_state:
    st.session_state.history = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

def find_rank_with_viewers(target_name, status_placeholder):
    target_name = target_name.lower().strip()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = None
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://chaturbate.com/?page=1")
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except: pass 

        global_count = 0
        for page_num in range(1, 31):
            if not st.session_state.is_running: break
            if page_num > 1: driver.get(f"https://chaturbate.com/?page={page_num}")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.roomCard')))
            room_cards = driver.find_elements(By.CSS_SELECTOR, 'li.roomCard')
            for index, card in enumerate(room_cards):
                try:
                    user_tag = card.find_element(By.CSS_SELECTOR, 'a[data-testid="room-card-username"]')
                    if user_tag.text.lower().strip() == target_name:
                        raw_viewers = card.find_element(By.CLASS_NAME, "viewers").text.lower()
                        v_count = int(float(raw_viewers.replace('k', '')) * 1000) if 'k' in raw_viewers else int(''.join(filter(str.isdigit, raw_viewers)))
                        return {"found": True, "page": page_num, "pos": index+1, "rank": global_count+index+1, "viewers": v_count}
                except: continue 
            global_count += len(room_cards)
    except Exception as e: return {"found": False, "error": str(e)}
    finally:
        if driver: driver.quit()
    return {"found": False}

# Sidebar
with st.sidebar:
    st.header("DATA ENGINE")
    target_input = st.text_input("Target Model", placeholder="sara_smoke")
    interval_input = st.number_input("Refresh Rate (Mins)", min_value=1, value=5)
    if st.button("START TRACKING"): st.session_state.is_running = True
    if st.button("STOP & RESET"):
        st.session_state.is_running = False
        st.session_state.history = []
        st.rerun()

# Main Dashboard
st.title("📊 STRATEGIC RANK ANALYTICS")
status_area = st.empty()
metric_cols = st.columns(4)

# Define Layout Order: Table First, then Visuals
log_container = st.container()
st.divider()
visuals_container = st.container()

if st.session_state.is_running and target_input:
    while st.session_state.is_running:
        status_area.info(f"Analyzing {target_input.upper()}...")
        result = find_rank_with_viewers(target_input, status_area)
        finish_time = datetime.now(user_tz).strftime("%H:%M")
        
        if result.get("found"):
            current_rank = result['rank']
            current_viewers = result['viewers']
            trend_html = '<span style="color: #888;">▬</span>'
            
            if len(st.session_state.history) > 0:
                prev_rank = st.session_state.history[0]["RAW_RANK"]
                if current_rank < prev_rank:
                    trend_html = '<span style="color: #00cc66; font-size:20px;">▲</span>'
                elif current_rank > prev_rank:
                    trend_html = '<span style="color: #ff4d4d; font-size:20px;">▼</span>'

            entry = {
                "TIME": finish_time,
                "RANK": f"#{current_rank}",
                "VIEWERS": f"{current_viewers:,}",
                "LOCATION": f"P{result['page']} P{result['pos']} {trend_html}", 
                "RAW_RANK": current_rank,
                "RAW_VIEWERS": current_viewers
            }
            st.session_state.history.insert(0, entry)

            # Update Metrics
            with metric_cols[0]: st.metric("Current Rank", f"#{current_rank}", delta_color="inverse")
            with metric_cols[1]: st.metric("Viewers", f"{current_viewers:,}")
            with metric_cols[2]: st.metric("Peak Rank Today", f"#{min([x['RAW_RANK'] for x in st.session_state.history])}")
            
            if len(st.session_state.history) > 2:
                df_temp = pd.DataFrame(st.session_state.history)
                corr = df_temp['RAW_VIEWERS'].corr(df_temp['RAW_RANK'])
                with metric_cols[3]: st.metric("Influence Score", f"{abs(corr):.2f}")

        # --- DISPLAY SECTION ---
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            
            # 1. TABLE FIRST
            with log_container:
                st.subheader("Live History Log")
                display_df = df.drop(columns=['RAW_RANK', 'RAW_VIEWERS'])
                st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            # 2. VISUALS BELOW
            if len(st.session_state.history) > 1:
                with visuals_container:
                    # Line Charts
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Viewer Volume")
                        st.area_chart(df.set_index("TIME")["RAW_VIEWERS"], color="#00cc66")
                    with c2:
                        st.subheader("Rank Trend")
                        st.line_chart(df.set_index("TIME")["RAW_RANK"], color="#ff4d4d")

                    # Scatter Plot
                    st.subheader("Scatter Plot Analysis (Trendline)")
                    fig = px.scatter(
                        df, x="RAW_VIEWERS", y="RAW_RANK", 
                        trendline="ols",
                        labels={"RAW_VIEWERS": "Viewers", "RAW_RANK": "Rank"},
                        template="plotly_white"
                    )
                    fig.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig, use_container_with_width=True)
        
        for i in range(interval_input * 60, 0, -1):
            if not st.session_state.is_running: break
            time.sleep(1)
else:
    st.info("System Ready. Enter a model name to begin.")
