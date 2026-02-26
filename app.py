import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Page Configuration
st.set_page_config(page_title="Model Rank Tracker Pro", layout="wide", page_icon="📊")

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

        # Get Max Pages
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
                            # Sanitize viewer count (handling 'k' and decimals)
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
    run_tracker = st.checkbox("Start Tracking")
    
    st.divider()
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

# --- Main Dashboard ---
st.title("📊 Model Performance Dashboard")

if run_tracker and target_input:
    st.info(f"Tracking **{target_input}** every {interval_input} minute(s).")
    dashboard_area = st.empty()
    
    while run_tracker:
        result = find_rank_with_viewers(target_input)
        now = datetime.now().strftime("%H:%M:%S")
        
        with dashboard_area.container():
            if result.get("found"):
                # Append to history
                st.session_state.history.append({
                    "Time": now, 
                    "Overall Rank": result['overall_rank'], 
                    "Viewers": result['viewers'], 
                    "Page": result['page'],
                    "Page Position": result['position']
                })
                
                # Metrics
                st.success(f"### Update for {target_input} at {now}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Overall Rank", f"#{result['overall_rank']}")
                m2.metric("Viewers", f"{result['viewers']:,}")
                m3.metric("Page", f"Page {result['page']}")
                m4.metric("Position on Page", f"Pos {result['position']}")
                
                # Plotly Dual-Axis Graph
                df = pd.DataFrame(st.session_state.history)
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Viewers Trace
                fig.add_trace(
                    go.Scatter(x=df["Time"], y=df["Viewers"], name="Viewers", 
                               mode='lines+markers', line=dict(color="#00CC96")),
                    secondary_y=False,
                )

                # Rank Trace
                fig.add_trace(
                    go.Scatter(x=df["Time"], y=df["Overall Rank"], name="Overall Rank", 
                               mode='lines+markers', line=dict(color="#EF553B"),
                               customdata=df[['Page', 'Page Position']],
                               hovertemplate="Rank: #%{y}<br>Page: %{customdata[0]}<br>Pos: %{customdata[1]}<extra></extra>"),
                    secondary_y=True,
                )

                fig.update_yaxes(title_text="Viewers", secondary_y=False)
                fig.update_yaxes(title_text="Overall Rank", secondary_y=True, autorange="reversed")
                fig.update_layout(title="Viewer & Rank Trends (Hover for Page details)", hovermode="x unified")
                
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Session History Log")
                st.dataframe(df.iloc[::-1], use_container_width=True)
            else:
                st.warning(f"[{now}] Model not found.")
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                if st.session_state.history:
                    st.dataframe(pd.DataFrame(st.session_state.history).iloc[::-1], use_container_width=True)

        time.sleep(interval_input * 60)
        st.rerun()
else:
    st.info("Enter a name and toggle 'Start Tracking' in the sidebar.")
