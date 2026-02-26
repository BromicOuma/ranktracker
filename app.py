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
st.set_page_config(page_title="Global Rank Tracker", layout="wide", page_icon="🌎")

# --- AUTO-TIMEZONE DETECTION ---
# This small piece of JS tells us the user's specific timezone (e.g., 'Europe/Berlin')
browser_tz_name = streamlit_js_eval(js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone", key="tz_eval")

# Default to UTC if detection is still loading or fails
user_tz = pytz.timezone(browser_tz_name) if browser_tz_name else pytz.utc

# Initialize tracking history
if 'history' not in st.session_state:
    st.session_state.history = []

def find_rank_with_viewers(target_name):
    target_name = target_name.lower().strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://chaturbate.com/?page=1")
        
        # Bypass Age Verification
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        global_count = 0
        # Check up to 50 pages
        for page_num in range(1, 51):
            if page_num > 1:
                driver.get(f"https://chaturbate.com/?page={page_num}")
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.roomCard')))
            room_cards = driver.find_elements(By.CSS_SELECTOR, 'li.roomCard')

            for index, card in enumerate(room_cards):
                try:
                    user_tag = card.find_element(By.CSS_SELECTOR, 'a[data-testid="room-card-username"]')
                    if user_tag.text.lower().strip() == target_name:
                        try:
                            raw_viewers = card.find_element(By.CLASS_NAME, "viewers").text.lower()
                            if 'k' in raw_viewers:
                                viewer_count = int(float(raw_viewers.replace('k', '')) * 1000)
                            else:
                                viewer_count = int(''.join(filter(str.isdigit, raw_viewers)))
                        except:
                            viewer_count = 0
                        
                        return {
                            "found": True, 
                            "page": page_num, 
                            "pos": index + 1, 
                            "rank": global_count + index + 1, 
                            "viewers": viewer_count,
                            "utc_now": datetime.now(pytz.utc) # Save in UTC
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
    st.header("Global Tracking")
    st.write(f"**Detected Timezone:** `{browser_tz_name if browser_tz_name else 'Detecting...'}`")
    
    st.divider()
    target_input = st.text_input("Model Name:", placeholder="e.g. sara_smoke")
    interval_input = st.number_input("Interval (Minutes):", min_value=1, value=5)
    
    col1, col2 = st.columns(2)
    with col1:
        start_tracking = st.button("Start Tracking")
    with col2:
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()

# --- Main Dashboard ---
st.title(" Live Rank Monitor")

status_area = st.empty()
log_area = st.empty()

if start_tracking and target_input:
    st.session_state.is_running = True
    
    while st.session_state.get('is_running', True):
        # Calculate local time for the status bar
        current_local = datetime.now(user_tz).strftime("%H:%M:%S")
        status_area.info(f"Searching for **{target_input}**... (Current Local Time: {current_local})")
        
        result = find_rank_with_viewers(target_input)
        
        if result.get("found"):
            # Store data with UTC timestamp
            entry = {
                "UTC_Time": result['utc_now'],
                "Overall Rank": f"#{result['rank']}", 
                "Viewers": f"{result['viewers']:,}", 
                "Location": f"Page {result['page']}, Pos {result['pos']}"
            }
            st.session_state.history.insert(0, entry)
            status_area.success(f" {target_input} at positon {Location.result['pos']} page {Location.{result['page']}}" overall rank is {result['rank'] )
        else:
            status_area.warning(f"[{datetime.now(user_tz).strftime('%H:%M:%S')}] Model not found.")
            if "error" in result:
                st.error(f"Error: {result['error']}")

        # Render Log Table
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            
            # Key feature: Convert UTC to the user's specific browser time on the fly
            df['Local Time'] = df['UTC_Time'].apply(lambda x: x.astimezone(user_tz).strftime("%H:%M:%S"))
            
            with log_area.container():
                st.subheader(f"History Log")
                st.table(df[['Local Time', 'Overall Rank', 'Viewers', 'Location']])
        
        time.sleep(interval_input * 60)
else:
    st.info(" Enter a model name and click 'Start Tracking' to begin. Your local timezone will be detected automatically.")
