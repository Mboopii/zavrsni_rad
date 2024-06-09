import gspread
import time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from hep import dohvati_podatke_hep
from vio import dohvati_podatke_vio
from gpz import dohvati_podatke_gpz
from a1 import dohvati_podatke_a1
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from google.oauth2.service_account import Credentials
from pdf import pdf_bp
import threading
import os
import uuid

creds = Credentials.from_service_account_file('api_keys/drive.json')
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Register the PDF blueprint
app.register_blueprint(pdf_bp, url_prefix='/pdf')

# Store the status of each request
request_status = {}
lock = threading.Lock()

def prijava(korisnicko_ime, lozinka, stranica):
    chromedriver_path = '/usr/local/bin/chromedriver'
    chrome_executable_path = '/usr/bin/google-chrome'

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = chrome_executable_path
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--disable-gpu')

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    if stranica == 'hep':
        login_url = 'https://mojracun.hep.hr/elektra/index.html#!/login'
        driver.get(login_url)

        username_field = driver.find_element('id', 'email')
        password_field = driver.find_element('id', 'inPwd')
        
        username_field.send_keys(korisnicko_ime)
        password_field.send_keys(lozinka)

        uvjeti_checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[ng-model="uvjetiKoristenja"]'))
        )
        uvjeti_checkbox.click()

        password_field.send_keys(Keys.RETURN)

        time.sleep(3)
        
    elif stranica == 'vio':
        login_url = 'https://www.vio.hr/mojvio/'
        driver.get(login_url)
        
        username_field = driver.find_element('id', 'email')
        password_field = driver.find_element('id', 'pass')
        
        username_field.send_keys(korisnicko_ime)
        password_field.send_keys(lozinka)
        
        password_field.send_keys(Keys.RETURN)
        
        driver.get('https://www.vio.hr/mojvio/?v=uplate')
        time.sleep(1)
        
    elif stranica == 'gpz':
        login_url = 'https://mojracun.gpz-opskrba.hr/login.aspx'
        driver.get(login_url)
        
        username_field = driver.find_element('id', 'email')
        password_field = driver.find_element('id', 'password')
        
        username_field.send_keys(korisnicko_ime)
        password_field.send_keys(lozinka)
        
        password_field.send_keys(Keys.RETURN)
        
    elif stranica == 'a1':
        login_url = 'https://moj.a1.hr/prijava'
        driver.get(login_url)

        username_field = driver.find_element(By.ID, 'fm_login_user')
        password_field = driver.find_element(By.ID, 'fm_login_pass')
        login_button = driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-primary')

        username_field.send_keys(korisnicko_ime)
        password_field.send_keys(lozinka)
        login_button.click()

        driver.get('https://moj.a1.hr/postpaid/residential/pregled-racuna')

    return driver

def create_worksheets(spreadsheet):
    for ws_name in ["hep", "vio", "gpz", "a1"]:
        if ws_name not in [ws.title for ws in spreadsheet.worksheets()]:
            spreadsheet.add_worksheet(title=ws_name, rows="100", cols="100")
            print(f"Worksheet '{ws_name}' izrađen.")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()

        korisnicko_ime = data.get('email')
        lozinka = data.get('password')
        stranica = data.get('selectedPage')

        print(korisnicko_ime)
        print(lozinka)
        print(stranica)

        request_id = str(uuid.uuid4())
        with lock:
            request_status[request_id] = 'processing'

        def process_request(request_id, korisnicko_ime, lozinka, stranica):
            try:
                driver = prijava(korisnicko_ime, lozinka, stranica)

                gc = gspread.service_account(filename='api_keys/racuni.json')
                spreadsheet = gc.open("Računi")

                create_worksheets(spreadsheet)
                worksheet = spreadsheet.worksheet(stranica)

                if worksheet is None:
                    print(f'Error: Worksheet "{stranica}" not found or created.')
                    with lock:
                        request_status[request_id] = 'error'
                    return

                if stranica == 'vio':
                    dohvati_podatke_vio(driver, worksheet)
                elif stranica == 'hep':
                    dohvati_podatke_hep(driver, worksheet)
                elif stranica == 'gpz':
                    dohvati_podatke_gpz(driver, worksheet)
                elif stranica == 'a1':
                    dohvati_podatke_a1(driver, worksheet)
                        
                driver.quit()
                with lock:
                    request_status[request_id] = 'completed'
                print(f'Podatci uspješno upisani u Google Sheets - Worksheet: {stranica}')
            except Exception as e:
                with lock:
                    request_status[request_id] = 'error'
                print(f'Greška pri prikupljanju podataka: {str(e)}')

        thread = threading.Thread(target=process_request, args=(request_id, korisnicko_ime, lozinka, stranica))
        thread.start()

        return jsonify({'request_id': request_id}), 202

    return render_template('index.html')

@app.route('/status/<request_id>', methods=['GET'])
def get_status(request_id):
    with lock:
        status = request_status.get(request_id, 'unknown')
    return jsonify({'status': status})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
