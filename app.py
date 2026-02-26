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
st.set_page_config(page_title="Model Tracker Pro", layout="wide", page_icon="📊")

# Initialize tracking history
if 'history' not in st.session_state:
    st.session_state.history = []

def find_rank_with_viewers(target_name):
    target_name = target_name.lower().strip()
    
    # Setup Chrome Options for Cloud Linux
    options = Options()
    options.add_argument("--headless=new") # Optimized headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        # On Streamlit Cloud, calling Chrome() without a path works 
        # because packages.txt puts chromedriver in the system PATH.
        driver = webdriver.Chrome(options=options)
        driver.get("https://chaturbate.com/?page=1")
        
        # Bypass Age Verification
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        # Get Max Pages
        try:
            last_page_el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-paction-name="LastPage"]')))
            max_pages = int(last_page_el.text)
        except:
            max_pages = 50 # Cloud fallback

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
                            viewer_text = card.find_element(By.CLASS_NAME, "viewers").text
                        except:
                            viewer_text = "N/A"
                        
                        rank = global_count + index + 1
                        return {"found": True, "page": page_num, "rank": rank, "viewers": viewer_text}
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
    run_tracker = st.checkbox("Start Tracking")
    
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

# --- Dashboard Layout ---
st.title("📊 Chaturbate Rank Tracker")

if run_tracker and target_input:
    st.info(f"Tracking **{target_input}** every {interval_input} minute(s).")
    dashboard_area = st.empty()
    
    while run_tracker:
        result = find_rank_with_viewers(target_input)
        now = datetime.now().strftime("%H:%M:%S")
        
        with dashboard_area.container():
            if result.get("found"):
                # Save to history
                st.session_state.history.insert(0, {
                    "Time": now, 
                    "Rank": result['rank'], 
                    "Viewers": result['viewers'], 
                    "Page": result['page']
                })
                
                st.success(f"### Found at {now}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Rank", f"#{result['rank']}")
                col2.metric("Viewers", result['viewers'])
                col3.metric("Page", result['page'])
            else:
                st.warning(f"[{now}] Model not found.")
                if "error" in result:
                    st.error(f"Error: {result['error']}")

            # Display History Table
            if st.session_state.history:
                st.divider()
                st.subheader("Session History")
                df = pd.DataFrame(st.session_state.history)
                st.dataframe(df, use_container_width=True)

        time.sleep(interval_input * 60)
        st.rerun()
else:
    st.info("👈 Enter a name and check the box in the sidebar to start.")
