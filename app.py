import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime

# Streamlit Page Config
st.set_page_config(page_title="Model Rank Tracker", page_icon="📈")

st.title("📈 Model Rank & Viewer Tracker")
st.markdown("Enter the model name and interval to start tracking.")

def find_rank_with_viewers(target_name):
    target_name = target_name.lower().strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Use the ChromeDriverManager but optimized for cloud environments
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    global_count = 0
    try:
        driver.get("https://chaturbate.com/?page=1")
        
        # 1. Verification bypass
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except:
            pass 

        # 2. Get Max Pages
        try:
            last_page_el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-paction-name="LastPage"]')))
            max_pages = int(last_page_el.text)
        except:
            max_pages = 60 # Safety fallback for web

        # 3. Search Loop
        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                driver.get(f"https://chaturbate.com/?page={page_num}")
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.roomCard')))
            room_cards = driver.find_elements(By.CSS_SELECTOR, 'li.roomCard')

            for index, card in enumerate(room_cards):
                try:
                    user_tag = card.find_element(By.CSS_SELECTOR, 'a[data-testid="room-card-username"]')
                    if user_tag.text.lower().strip() == target_name:
                        try: viewer_text = card.find_element(By.CLASS_NAME, "viewers").text
                        except: viewer_text = "N/A"
                        
                        rank = global_count + index + 1
                        driver.quit()
                        return {"found": True, "page": page_num, "pos": index + 1, "rank": rank, "viewers": viewer_text}
                except:
                    continue 

            global_count += len(room_cards)
        
    except Exception as e:
        st.error(f"Error during search: {e}")
    
    driver.quit()
    return {"found": False}

# --- UI Layout ---
with st.sidebar:
    target = st.text_input("Model's Name:", placeholder="e.g. sara_smoke")
    interval = st.number_input("Interval (Minutes):", min_value=1, value=5)
    start_button = st.button("Start Tracking")

if start_button and target:
    st.info(f"Tracking started for **{target}**. Refresh the page to stop.")
    
    # Placeholder for the latest result to avoid messy scrolling
    result_container = st.empty()

    while True:
        with st.spinner(f"Searching for {target}..."):
            result = find_rank_with_viewers(target)
        
        with result_container.container():
            if result["found"]:
                st.success(f"### Found at {datetime.now().strftime('%H:%M:%S')}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Rank", f"#{result['rank']}")
                col2.metric("Viewers", result['viewers'])
                col3.metric("Location", f"Page {result['page']}")
            else:
                st.warning(f"Performer '{target}' not found at {datetime.now().strftime('%H:%M:%S')}")
        
        time.sleep(interval * 60)