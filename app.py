import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import pandas as pd
import pytz
from streamlit_js_eval import streamlit_js_eval

# 1. Page Configuration
st.set_page_config(page_title="Model Rank Tracker", layout="wide", page_icon="📝")

# Custom CSS
st.markdown("""
    <style>
    .big-bold { font-size:22px !important; font-weight: bold; }
    .stAlert { border: 2px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- AUTO-TIMEZONE DETECTION ---
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
    options.add_argument("--disable-gpu")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        # Set a timeout so it doesn't freeze forever if the site is slow
        driver.set_page_load_timeout(30) 
        driver.get("https://chaturbate.com/?page=1")
        
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        global_count = 0
        # Reduced to 30 pages for faster response/less freezing
        for page_num in range(1, 31):
            # Update the UI every few pages so the user knows it's moving
            if page_num % 5 == 0:
                status_placeholder.info(f"🔎 Currently on **Page {page_num}** searching for **{target_input.upper()}**...")
            
            if page_num > 1:
                driver.get(f"https://chaturbate.com/?page={page_num}")
            
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.roomCard')))
            room_cards = driver.find_elements(By.CSS_SELECTOR, 'li.roomCard')

            for index, card in enumerate(room_cards):
                try:
                    user_tag = card.find_element(By.CSS_SELECTOR, 'a[data-testid="room-card-username"]')
                    if user_tag.text.lower().strip() == target_name:
                        raw_viewers = card.find_element(By.CLASS_NAME, "viewers").text.lower()
                        v_count = int(float(raw_viewers.replace('k', '')) * 1000) if 'k' in raw_viewers else int(''.join(filter(str.isdigit, raw_viewers)))
                        return {"found": True, "page": page_num, "pos": index+1, "rank": global_count+index+1, "viewers": v_count, "utc": datetime.now(pytz.utc)}
                except:
                    continue 
            global_count += len(room_cards)
            
    except Exception as e:
        return {"found": False, "error": str(e)}
    finally:
        if driver:
            driver.quit()
    return {"found": False}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ **SETTINGS**")
    target_input = st.text_input("Model Name:", placeholder="e.g. sara_smoke")
    interval_input = st.number_input("Interval (Minutes):", min_value=1, value=5)
    
    if st.button("🚀 START TRACKING"):
        st.session_state.is_running = True
    
    if st.button("🛑 STOP & RESET"):
        st.session_state.is_running = False
        st.session_state.history = []
        st.rerun()

# --- Main Dashboard ---
st.title("🔍 **SEARCH & RANK MODEL**")
status_area = st.empty()
log_area = st.empty()

if st.session_state.is_running and target_input:
    while st.session_state.is_running:
        local_now = datetime.now(user_tz).strftime("%H:%M:%S")
        status_area.info(f"🔎 **Initiating Search for {target_input.upper()}...** (Local Time: {local_now})")
        
        result = find_rank_with_viewers(target_input, status_area)
        
        finish_time = datetime.now(user_tz).strftime("%H:%M:%S")
        if result.get("found"):
            entry = {
                "TIME": f"**{finish_time}**",
                "OVERALL RANK": f"**#{result['rank']}**", 
                "VIEWERS": f"**{result['viewers']:,}**", 
                "LOCATION": f"**Page {result['page']}, Pos {result['pos']}**",
                "sort_time": result['utc']
            }
            st.session_state.history.insert(0, entry)
            status_area.success(f"### ✅ **{target_input.upper()} FOUND!** \n\n **POSITION {result['pos']} | PAGE {result['page']} | RANK: #{result['rank']}**")
        else:
            status_area.warning(f"⚠️ **[{finish_time}] {target_input.upper()} NOT FOUND.**")
            if "error" in result:
                st.error(f"Browser Error: {result['error']}")

        if st.session_state.history:
            with log_area.container():
                st.markdown(f"### 📊 **HISTORY LOG ({browser_tz_name})**")
                st.table(pd.DataFrame(st.session_state.history).drop(columns=['sort_time']))
        
        # This is where most freezes happen. We countdown so you see it's alive.
        for i in range(interval_input * 60, 0, -1):
            if not st.session_state.is_running: break
            status_area.info(f"⏱️ **Next check in {i} seconds...** (Model: {target_input.upper()})")
            time.sleep(1)
else:
    st.info("👈 **Enter a name and click 'Start Tracking' to begin.**")
