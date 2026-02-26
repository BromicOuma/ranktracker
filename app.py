import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Model Tracker Pro", layout="wide")

st.title("📊 Model Rank & Viewer Tracker")

# Initialize session state for history
if 'history' not in st.session_state:
    st.session_state.history = []

def find_rank_with_viewers(target_name):
    target_name = target_name.lower().strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Specific paths for Streamlit Cloud Linux environment
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    service = Service("/usr/bin/chromedriver")

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://chaturbate.com/?page=1")
        
        # 1. Close overlay
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        # 2. Get Max Pages
        try:
            last_page_el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-paction-name="LastPage"]')))
            max_pages = int(last_page_el.text)
        except:
            max_pages = 60 

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
                        driver.quit()
                        return {"found": True, "page": page_num, "rank": rank, "viewers": viewer_text}
                except:
                    continue 
            global_count += len(room_cards)
            
        driver.quit()
    except Exception as e:
        return {"found": False, "error": str(e)}
    
    return {"found": False}

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Settings")
    target = st.text_input("Model Name", placeholder="e.g. sara_smoke")
    interval = st.number_input("Check every (minutes)", min_value=1, value=5)
    run_tracker = st.checkbox("Run Tracker")

# --- Main Logic ---
if run_tracker and target:
    st.info(f"Tracking **{target}** every {interval} minute(s).")
    placeholder = st.empty()
    
    while run_tracker:
        result = find_rank_with_viewers(target)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if result.get("found"):
            # Update history
            new_data = {
                "Time": timestamp, 
                "Rank": result['rank'], 
                "Viewers": result['viewers'], 
                "Page": result['page']
            }
            st.session_state.history.insert(0, new_data)
            
            with placeholder.container():
                st.success(f"### Latest Update: {timestamp}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Current Rank", f"#{result['rank']}")
                c2.metric("Viewers", result['viewers'])
                c3.metric("Page", result['page'])
                
                st.divider()
                st.subheader("History Log")
                st.table(pd.DataFrame(st.session_state.history))
        else:
            st.warning(f"[{timestamp}] Model not found or error occurred.")
            if "error" in result:
                st.error(result["error"])

        time.sleep(interval * 60)
        st.rerun() # Refresh the UI
else:
    st.write("Enter a name and check the box in the sidebar to start.")