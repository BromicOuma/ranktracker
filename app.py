import sys
import time
import os
import pandas as pd
from datetime import datetime
from multiprocessing import Pool, cpu_count
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# Terminal encoding fix
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CSV_FILE = "rank_history.csv"
DASHBOARD_FILE = "rank_dashboard.png"

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def check_page(args):
    page_num, target_name = args
    driver = get_driver()
    url = f"https://chaturbate.com/?page={page_num}"
    result = None
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "close_entrance_terms"))).click()
        except: pass
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.roomCard')))
        cards = driver.find_elements(By.CSS_SELECTOR, 'li.roomCard')
        for index, card in enumerate(cards):
            try:
                username = card.find_element(By.CSS_SELECTOR, 'a[data-testid="room-card-username"]').text.lower().strip()
                if username == target_name:
                    viewers = card.find_element(By.CLASS_NAME, "viewers").text
                    v_count = viewers.split()[0].replace(',', '')
                    result = {"page": page_num, "pos": index + 1, "viewers": v_count}
                    break
            except: continue
    finally:
        driver.quit()
    return result

def get_trend_indicator(current_rank):
    """Compares current rank to previous rank in CSV and returns arrow/color."""
    if not os.path.exists(CSV_FILE):
        return "—", "white" # No data yet

    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty: return "—", "white"
        
        last_entry = df.iloc[-1]
        previous_rank = (last_entry['page'] - 1) * 60 + last_entry['pos']
        
        if current_rank < previous_rank:
            return "▲", "green"  # Rank improved (number got smaller)
        elif current_rank > previous_rank:
            return "▼", "red"    # Rank dropped (number got larger)
        else:
            return "—", "grey"
    except:
        return "—", "white"

def update_dashboard(target_name):
    if not os.path.exists(CSV_FILE): return
    df = pd.read_csv(CSV_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['rank'] = (df['page'] - 1) * 60 + df['pos']

    plt.style.use('dark_background')
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['rank'], marker='o', linestyle='-', color='#2ecc71', linewidth=2)
    
    plt.gca().invert_yaxis() 
    plt.title(f"LIVE RANKING: {target_name.upper()}", fontsize=14, color='white', pad=20)
    plt.grid(True, alpha=0.2)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(DASHBOARD_FILE)

if __name__ == "__main__":
    target = "mollyflwers"
    
    # 1. Get Page Count
    temp_driver = get_driver()
    temp_driver.get("https://chaturbate.com/")
    try:
        last_page = int(temp_driver.find_element(By.CSS_SELECTOR, 'li[data-paction-name="LastPage"] a').text)
    except: last_page = 62
    temp_driver.quit()

    # 2. Parallel Search
    tasks = [(p, target) for p in range(1, last_page + 1)]
    found_data = None
    with Pool(min(cpu_count(), 4)) as pool:
        for result in tqdm(pool.imap_unordered(check_page, tasks), total=last_page, desc="Scanning Cams"):
            if result:
                found_data = result
                pool.terminate()
                break

    # 3. Calculate Trend and Log
    curr_rank = (found_data['page'] - 1) * 60 + found_data['pos'] if found_data else 9999
    arrow, color = get_trend_indicator(curr_rank)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_entry = {
        "timestamp": timestamp, 
        "name": target, 
        "page": found_data['page'] if found_data else 999, 
        "pos": found_data['pos'] if found_data else 999, 
        "viewers": found_data['viewers'] if found_data else 0,
        "trend": arrow
    }
    
    pd.DataFrame([new_entry]).to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False)
    
    # 4. Final Terminal Output with Trend
    print("\n" + "="*40)
    print(f"PERFORMER: {target}")
    if found_data:
        print(f"RANK:      #{curr_rank} {arrow} (Page {found_data['page']}, Pos {found_data['pos']})")
        print(f"VIEWERS:   {found_data['viewers']}")
    else:
        print(f"STATUS:    Offline or Not Found {arrow}")
    print("="*40)

    update_dashboard(target)
