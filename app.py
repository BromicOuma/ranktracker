import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Model Rank Tracker", layout="wide", page_icon="📝")

# Initialize tracking history in session state
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
        
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        try:
            last_page_el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-paction-name="LastPage"]')))
            max_pages = int(last_page_el.text)
        except:
            max_pages = 50 

        global_count = 0
        for page_num in range(1, max_pages + 1):
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
                        
                        pos_on_page = index + 1
                        overall_rank = global_count + pos_on_page
                        
                        return {
                            "found": True, 
                            "page": page_num, 
                            "position": pos_on_page, 
                            "overall_rank": overall_rank, 
                            "viewers": viewer_count
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
    st.header("Search Settings")
    target_input = st.text_input("Model Name:", placeholder="e.g. sara_smoke")
    interval_input = st.number_input("Check Interval (Minutes):", min_value=1, value=5)
    run_tracker = st.button("Start Tracking")
    stop_tracker = st.button("Stop Tracking")
    
    st.divider()
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

# --- Main Dashboard ---
st.title("📝 Model History Log")

# Create two specific areas that we can update without refreshing the whole page
status_area = st.empty()
log_area = st.empty()

if run_tracker:
    if not target_input:
        st.error("Please enter a model name in the sidebar.")
    else:
        st.session_state.is_running = True
        
        while st.session_state.get('is_running', False):
            now = datetime.now().strftime("%H:%M:%S")
            
            # 1. Update status to 'Searching'
            status_area.info(f"🔎 Currently searching for **{target_input}**... (Last check: {now})")
            
            result = find_rank_with_viewers(target_input)
            
            if result.get("found"):
                # Add to history
                entry = {
                    "Time": datetime.now().strftime("%H:%M:%S"), 
                    "Overall Rank": f"#{result['overall_rank']}", 
                    "Viewers": f"{result['viewers']:,}", 
                    "Page": result['page'],
                    "Page Position": result['position']
                }
                st.session_state.history.insert(0, entry) # Most recent at top
                
                status_area.success(f"✅ Last Found: {target_input} at {now} (Rank #{result['overall_rank']})")
            else:
                status_area.warning(f"⚠️ [{now}] Model not found. Will retry in {interval_input} min.")
                if "error" in result:
                    st.error(f"Technical Error: {result['error']}")

            # 2. Update the History Table without refreshing the page
            with log_area.container():
                if st.session_state.history:
                    st.subheader("Data Log")
                    st.table(pd.DataFrame(st.session_state.history))
            
            # Sleep until next check
            time.sleep(interval_input * 60)

elif not st.session_state.history:
    st.info("👈 Enter a name and click 'Start Tracking' to begin recording data.")
else:
    # If the tracker isn't running but we have history, keep showing the log
    with log_area.container():
        st.subheader("Data Log (Stopped)")
        st.table(pd.DataFrame(st.session_state.history))
