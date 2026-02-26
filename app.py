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

# Page Configuration
st.set_page_config(page_title="Model Rank Tracker Pro", layout="wide")

# Custom CSS for high-visibility table
st.markdown("""
    <style>
    table { width: 100% !important; font-family: sans-serif; border-collapse: collapse; }
    th { background-color: #f0f2f6; color: #31333F; font-weight: bold; padding: 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #e6e9ef; font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Auto-Timezone Detection
browser_tz_name = streamlit_js_eval(js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone", key="tz_eval")
user_tz = pytz.timezone(browser_tz_name) if browser_tz_name else pytz.utc

# Initialize Session State
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
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        driver.get("https://chaturbate.com/?page=1")
        
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        global_count = 0
        for page_num in range(1, 31):
            if not st.session_state.is_running: break
            if page_num % 5 == 0 or page_num == 1:
                status_placeholder.info(f"Scanning Page {page_num} for {target_name.upper()}")
            
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
                        return {"found": True, "page": page_num, "pos": index+1, "rank": global_count+index+1, "viewers": v_count, "utc": datetime.now(pytz.utc)}
                except:
                    continue 
            global_count += len(room_cards)
    except Exception as e:
        return {"found": False, "error": str(e)}
    finally:
        if driver: driver.quit()
    return {"found": False}

# Sidebar
with st.sidebar:
    st.header("SETTINGS")
    target_input = st.text_input("Model Name", placeholder="sara_smoke")
    interval_input = st.number_input("Interval Minutes", min_value=1, value=5)
    
    if st.button("START TRACKING"):
        st.session_state.is_running = True
    
    if st.button("STOP AND CLEAR"):
        st.session_state.is_running = False
        st.session_state.history = []
        st.rerun()

# Main UI
st.title("SEARCH AND RANK MODEL")
status_area = st.empty()
log_area = st.empty()

if st.session_state.is_running and target_input:
    while st.session_state.is_running:
        local_now = datetime.now(user_tz).strftime("%H:%M:%S")
        status_area.info(f"Searching for {target_input.upper()}... Time: {local_now}")
        
        result = find_rank_with_viewers(target_input, status_area)
        finish_time = datetime.now(user_tz).strftime("%H:%M:%S")
        
        if result.get("found"):
            current_rank = result['rank']
            trend_html = '<span style="color: #888888;">▬</span>' # Default
            
            if len(st.session_state.history) > 0:
                prev_rank = st.session_state.history[0]["RAW_RANK"]
                if current_rank < prev_rank:
                    trend_html = '<span style="color: #00cc66; font-size: 24px;">▲</span>' # Rank Improved
                elif current_rank > prev_rank:
                    trend_html = '<span style="color: #ff4d4d; font-size: 24px;">▼</span>' # Rank Dropped

            entry = {
                "TIME": finish_time,
                "TREND": trend_html,
                "OVERALL RANK": f"#{current_rank}",
                "VIEWERS": f"{result['viewers']:,}",
                "LOCATION": f"Page {result['page']}, Position {result['pos']}",
                "RAW_RANK": current_rank
            }
            st.session_state.history.insert(0, entry)
            status_area.success(f"FOUND: {target_input.upper()} RANK {current_rank}")
        else:
            status_area.warning(f"NOT FOUND: {target_input.upper()} at {finish_time}")

        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history).drop(columns=['RAW_RANK'])
            with log_area.container():
                st.subheader(f"HISTORY LOG ({browser_tz_name})")
                # Using to_html to render the colored arrows correctly
                st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        for i in range(interval_input * 60, 0, -1):
            if not st.session_state.is_running: break
            status_area.info(f"Next check in {i} seconds for {target_input.upper()}")
            time.sleep(1)
else:
    st.info("Enter a name and click Start Tracking.")
