import sqlite3
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
from flask import Flask, jsonify
import threading
import re
from flask_cors import CORS
from flask import send_from_directory

DATABASE = 'data.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Create table with timestamp, water_level, flow and latest update
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            water_level REAL NOT NULL,
            flow REAL NOT NULL,
            latest_update TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    
def save_data(water_level, flow, latest_update):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current timestamp
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO water_data (timestamp, water_level, flow, latest_update)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, water_level, flow, latest_update))
    conn.commit()
    conn.close()
    print(f"Data saved: {timestamp}, {water_level}, {flow}, {latest_update}")

def fetch_water_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        water_level_str = soup.find('td', string="VattennivÃ¥ nedstrÃ¶ms kraftverket, m.Ã¶.h.").find_next('td').text.strip()
        water_level = float(water_level_str.replace(",", "."))  # Convert to float
        flow_str = soup.find_all('td', class_='tblborder pad w60 right bottom')[1].text.strip()
        flow = float(flow_str.replace(",", "."))  # Convert to float
        latest_update_str = soup.find('p', class_='gray').text.strip()
        latest_update_match = re.search(r'(\d.*)', latest_update_str)
        latest_update = latest_update_match.group(1) if latest_update_match else None


        return water_level, flow, latest_update
    else:
        print(f"Failed to fetch data from {url} (Status Code: {response.status_code})")
        return None, None, None
    
def fetch_and_store(url):
    water_level, flow, latest_update = fetch_water_data(url)
    if water_level is not None and flow is not None and latest_update is not None:
        save_data(water_level, flow, latest_update)
    else:
        print(f"At least one parameter was not found! The parameters returned as: Water level: [{water_level}] Flow: [{flow}] Latest update: [{latest_update}]")
app = Flask(__name__) # Initialize the Flask app
CORS(app)  # Allows frontend (port 5000) to access backend (port 5500)

@app.route('/') 
def serve_index(): 
    return send_from_directory('static', 'index.html')

@app.route('/list')
def serve_list():
    return send_from_directory('static', 'list.html')

@app.route('/dummy')
def serve_dummy():
    return send_from_directory('static', 'dummy.html')

@app.route('/data', methods=['GET'])
def get_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, water_level, flow, latest_update FROM water_data")
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

# Create database if not already exists
init_db()
# url = 'http://127.0.0.1:5500/dummy.html'  # Development URL
url = 'https://www.vkr.se/SlaHist/sla.htm' # Real URL

# Fetch and store data every 15 minutes
def fetch_periodically():
    print("Starting a new thread!")
    while True:
        print("Fetching and storing data...")
        fetch_and_store(url)
        print("Waiting for 15 minutes...")
        time.sleep(900)  # Wait for 900 seconds (15 minutes)

# Start the periodic fetch function in a separate thread
fetch_thread = threading.Thread(target=fetch_periodically)
fetch_thread.daemon = True  # This makes the thread exit when the main program exits
fetch_thread.start()

import os
print("Current working directory:", os.getcwd())
print("Static folder absolute path:", os.path.abspath('static'))
print("Files in static:", os.listdir('static'))

app.run(debug=True, use_reloader=False)  # Start the Flask server



