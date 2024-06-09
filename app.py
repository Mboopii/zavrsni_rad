import gspread
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from hep import dohvati_podatke_hep
from vio import dohvati_podatke_vio
from gpz import dohvati_podatke_gpz
from a1 import dohvati_podatke_a1
from google.oauth2.service_account import Credentials
from pdf import pdf_bp
import threading
import os
import uuid
from bs4 import BeautifulSoup

creds = Credentials.from_service_account_file('api_keys/drive.json')
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Register the PDF blueprint
app.register_blueprint(pdf_bp, url_prefix='/pdf')

request_status = {}
request_lock = threading.Lock()

def create_worksheets(spreadsheet):
    for ws_name in ["hep", "vio", "gpz", "a1"]:
        if ws_name not in [ws.title for ws in spreadsheet.worksheets()]:
            spreadsheet.add_worksheet(title=ws_name, rows="100", cols="100")
            print(f"Worksheet '{ws_name}' izrađen.")

def prijava(korisnicko_ime, lozinka, stranica):
    session = requests.Session()

    if stranica == 'hep':
        login_url = 'https://mojracun.hep.hr/elektra/index.html#!/login'
        response = session.get(login_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Example payload, adjust according to the actual form data
        login_payload = {
            'email': korisnicko_ime,
            'inPwd': lozinka,
            'uvjetiKoristenja': 'on'
        }

        login_submit_url = 'https://mojracun.hep.hr/elektra/api/login'
        session.post(login_submit_url, data=login_payload)

        data_url = 'https://mojracun.hep.hr/elektra/api/data'
        data_response = session.get(data_url)
        return data_response.json()

    elif stranica == 'vio':
        login_url = 'https://www.vio.hr/mojvio/'
        response = session.get(login_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        login_payload = {
            'email': korisnicko_ime,
            'pass': lozinka
        }

        login_submit_url = 'https://www.vio.hr/mojvio/login'
        session.post(login_submit_url, data=login_payload)

        data_url = 'https://www.vio.hr/mojvio/?v=uplate'
        data_response = session.get(data_url)
        return data_response.json()

    elif stranica == 'gpz':
        login_url = 'https://mojracun.gpz-opskrba.hr/login.aspx'
        response = session.get(login_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        login_payload = {
            'email': korisnicko_ime,
            'password': lozinka
        }

        login_submit_url = 'https://mojracun.gpz-opskrba.hr/login'
        session.post(login_submit_url, data=login_payload)

        data_url = 'https://mojracun.gpz-opskrba.hr/data'
        data_response = session.get(data_url)
        return data_response.json()

    elif stranica == 'a1':
        login_url = 'https://moj.a1.hr/prijava'
        response = session.get(login_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        login_payload = {
            'fm_login_user': korisnicko_ime,
            'fm_login_pass': lozinka
        }

        login_submit_url = 'https://moj.a1.hr/login'
        session.post(login_submit_url, data=login_payload)

        data_url = 'https://moj.a1.hr/postpaid/residential/pregled-racuna'
        data_response = session.get(data_url)
        return data_response.json()

def process_request(korisnicko_ime, lozinka, stranica, request_id):
    try:
        data = prijava(korisnicko_ime, lozinka, stranica)

        gc = gspread.service_account(filename='api_keys/racuni.json')
        spreadsheet = gc.open("Računi")

        create_worksheets(spreadsheet)
        worksheet = spreadsheet.worksheet(stranica)

        if worksheet is None:
            update_status(request_id, 'Error: Worksheet "{}" not found or created.'.format(stranica), False)
            return

        if stranica == 'vio':
            dohvati_podatke_vio(data, worksheet)
        elif stranica == 'hep':
            dohvati_podatke_hep(data, worksheet)
        elif stranica == 'gpz':
            dohvati_podatke_gpz(data, worksheet)
        elif stranica == 'a1':
            dohvati_podatke_a1(data, worksheet)
                
        update_status(request_id, 'Podatci uspješno upisani u Google Sheets - Worksheet: {}'.format(stranica), True)

    except Exception as e:
        update_status(request_id, 'Greška pri prikupljanju podataka: {}'.format(str(e)), False)

def update_status(request_id, message, success):
    with request_lock:
        request_status[request_id] = {'result': message, 'success': success}

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
        update_status(request_id, 'Request received and being processed.', None)

        thread = threading.Thread(target=process_request, args=(korisnicko_ime, lozinka, stranica, request_id))
        thread.start()

        return jsonify({'result': 'Zahtjev je primljen. Podatci se obrađuju za Worksheet: {}'.format(stranica), 'request_id': request_id}), 202

    return render_template('index.html')

@app.route('/status/<request_id>', methods=['GET'])
def check_status(request_id):
    with request_lock:
        status = request_status.get(request_id, None)
    if status:
        return jsonify(status), 200
    else:
        return jsonify({'status': 'unknown'}), 404

if __name__ == '__main__':
    pass