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
                            # Clean viewer string (e.g., "1.2k" or "500") to integer
                            raw_viewers = card.find_element(By.CLASS_NAME, "viewers").text.lower().replace('k', '000').replace('.', '')
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
    run_tracker = st.checkbox("Start Tracking")
    
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

# --- Dashboard Layout ---
st.title("Chaturbate Rank Dashboard")

if run_tracker and target_input:
    st.info(f"Tracking **{target_input}** every {interval_input} minute(s).")
    dashboard_area = st.empty()
    
    while run_tracker:
        result = find_rank_with_viewers(target_input)
        now = datetime.now().strftime("%H:%M:%S")
        
        with dashboard_area.container():
            if result.get("found"):
                # Save to history for graphing
                st.session_state.history.append({
                    "Time": now, 
                    "Overall Rank": result['overall_rank'], 
                    "Viewers": result['viewers'], 
                    "Page": result['page'],
                    "Page Position": result['position'],
                    "Location": f"P{result['page']} Pos{result['position']}"
                })
                
                st.success(f"### Found: {target_input} at {now}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Overall Rank", f"#{result['overall_rank']}")
                c2.metric("Viewers", f"{result['viewers']:,}")
                c3.metric("Page", f"Page {result['page']}")
                c4.metric("Page Position", f"Pos {result['position']}")
                
                # --- VISUALIZATION ---
                df = pd.DataFrame(st.session_state.history)
                
                st.divider()
                st.subheader("Viewer Trends")
                # Graphing Viewer Count over time
                st.line_chart(df.set_index("Time")[["Viewers"]])

                st.subheader("Rank History (Recent First)")
                st.dataframe(df.iloc[::-1], use_container_width=True)
            else:
                st.warning(f"[{now}] Model not found.")
                if "error" in result:
                    st.error(f"Error: {result['error']}")

        time.sleep(interval_input * 60)
        st.rerun()
else:
    st.info(" Set model name and interval in the sidebar, then toggle 'Start Tracking'.")
