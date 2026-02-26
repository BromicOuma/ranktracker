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
from streamlit_js_eval import streamlit_js_eval

# 1. Page Configuration
st.set_page_config(page_title="Model Rank Tracker Pro", layout="wide")

# Custom CSS for Bold UI
st.markdown("""
    <style>
    .stTable { font-size: 20px !important; }
    .css-1offfwp { font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- AUTO-TIMEZONE DETECTION ---
browser_tz_name = streamlit_js_eval(js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone", key="tz_eval")
user_tz = pytz.timezone(browser_tz_name) if browser_tz_name else pytz.utc

# Initialize Session States
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
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        # Explicit Service path for Streamlit Cloud Linux
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        driver.get("https://chaturbate.com/?page=1")
        
        # Age Gate Bypass
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        global_count = 0
        # Check up to 100 pages for stability
        for page_num in range(1, 100):
            if not st.session_state.is_running:
                break
                
            if page_num % 5 == 0:
                status_placeholder.info(f"**Scanning Page {page_num}...** (Current User: {target_name.upper()})")
            
            if page_num > 1:
                driver.get(f"https://chaturbate.com/?page={page_num}")
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.roomCard')))
            room_cards = driver.find_elements(By.CSS_SELECTOR, 'li.roomCard')

            for index, card in enumerate(room_cards):
                try:
                    user_tag = card.find_element(By.CSS_SELECTOR, 'a[data-testid="room-card-username"]')
                    if user_tag.text.lower().strip() == target_name:
                        raw_viewers = card.find_element(By.CLASS_NAME, "viewers").text.lower()
                        v_count = int(float(raw_viewers.replace('k', '')) * 1000) if 'k' in raw_viewers else int(''.join(filter(str.isdigit, raw_viewers)))
                        
                        return {
                            "found": True, 
                            "page": page_num, 
                            "pos": index + 1, 
                            "rank": global_count + index + 1, 
                            "viewers": v_count,
                            "utc_now": datetime.now(pytz.utc)
                        }
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
    st.header(" **SETTINGS**")
    st.write(f" Detected Timezone: **{browser_tz_name if browser_tz_name else 'Detecting...'}**")
    
    target_input = st.text_input("Model Name:", placeholder="e.g. sara_smoke")
    interval_input = st.number_input("Interval (Minutes):", min_value=1, value=5)
    
    if st.button(" **START TRACKING**"):
        st.session_state.is_running = True
    
    if st.button(" **STOP & CLEAR**"):
        st.session_state.is_running = False
        st.session_state.history = []
        st.rerun()

# --- Dashboard ---
st.title(" **SEARCH & RANK MODEL**")

status_area = st.empty()
log_area = st.empty()

if st.session_state.is_running and target_input:
    while st.session_state.is_running:
        local_now = datetime.now(user_tz).strftime("%H:%M:%S")
        status_area.info(f" **Initiating Search for {target_input.upper()}...** (Local Time: {local_now})")
        
        result = find_rank_with_viewers(target_input, status_area)
        
        finish_time = datetime.now(user_tz).strftime("%H:%M:%S")
        
        if result.get("found"):
            entry = {
                "TIME": f"**{finish_time}**",
                "OVERALL RANK": f"**#{result['rank']}**", 
                "VIEWERS": f"**{result['viewers']:,}**", 
                "LOCATION": f"**Page {result['page']}, Pos {result['pos']}**"
            }
            st.session_state.history.insert(0, entry)
            status_area.success(f"###  **{target_input.upper()} FOUND!** \n\n **POSITION {result['pos']} | PAGE {result['page']} | RANK: #{result['rank']}**")
        else:
            status_area.warning(f" **[{finish_time}] {target_input.upper()} NOT FOUND.**")
            if "error" in result:
                st.error(f"Browser Trace: {result['error']}")

        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            with log_area.container():
                st.markdown(f"###  **BOLD HISTORY LOG ({browser_tz_name})**")
                st.table(df)
        
        # Countdown to next check (Keeps the UI alive)
        for i in range(interval_input * 60, 0, -1):
            if not st.session_state.is_running:
                break
            status_area.info(f" **Next check in {i} seconds...** (Searching for: {target_input.upper()})")
            time.sleep(1)
else:
    st.info("  **Enter a model name and click 'Start Tracking' to begin.**")
