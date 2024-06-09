import gspread
import time
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
import requests
from bs4 import BeautifulSoup

creds = Credentials.from_service_account_file('api_keys/drive.json')
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Register the PDF blueprint
app.register_blueprint(pdf_bp, url_prefix='/pdf')

request_status = {}
request_lock = threading.Lock()

def prijava(korisnicko_ime, lozinka, stranica):
    session = requests.Session()

    if stranica == 'hep':
        login_url = 'https://mojracun.hep.hr/elektra/api/korisnik/prijava'
        login_payload = {
            'username': korisnicko_ime,
            'password': lozinka,
            'prva': True
        }
        headers = {
            'Content-Type': 'application/json'
        }
        response = session.post(login_url, json=login_payload, headers=headers)
        print(f"HEP login response: {response.status_code}, {response.content}")
        if response.status_code != 200:
            print(f"HEP login failed: {response.status_code}")
            return None
        
        auth_token = response.json().get('Token')
        kupac_id = response.json()['Korisnik']['Kupci'][0]['KupacId']
        if auth_token:
            session.headers.update({'Authorization': f'Bearer {auth_token}'})
        else:
            print("HEP login failed: No auth token found")
            return None

        return session, kupac_id

    elif stranica == 'vio':
        login_url = 'https://www.vio.hr/mojvio/?a=login'
        login_payload = {
            'email': korisnicko_ime,
            'pass': lozinka
        }
        response = session.post(login_url, data=login_payload)
        print(f"VIO login response: {response.status_code}, {response.content}")
        if response.status_code != 200:
            print(f"VIO login failed: {response.status_code}")
            return None

        return session

    elif stranica == 'gpz':
        login_url = 'https://mojracun.gpz-opskrba.hr/login.aspx'
        login_payload = {
            'IsItLogin': 'yes',
            'email': korisnicko_ime,
            'password': lozinka
        }
        response = session.post(login_url, data=login_payload, allow_redirects=False)
        print(f"GPZ login response: {response.status_code}, {response.content}")
        if response.status_code != 302:
            print(f"GPZ login failed: {response.status_code}")
            return None
        
        return session

    elif stranica == 'a1':
        login_url = 'https://webauth.a1.hr/vasmpauth/ProcessLoginServlet'
        login_payload = {
            'UserID': korisnicko_ime,
            'Password': lozinka,
            'userRequestURL': 'https://moj.a1.hr',
            'serviceRegistrationURL': '',
            'level': 30,
            'SetMsisdn': True,
            'service': '',
            'hashpassword': 123
        }
        response = session.post(login_url, data=login_payload, allow_redirects=False)
        print(f"A1 login response: {response.status_code}, {response.content}")
        if response.status_code != 302:
            print(f"A1 login failed: {response.status_code}")
            return None

        # Handle redirection after successful login
        redirected_url = response.headers.get('Location')
        if redirected_url:
            session.get(redirected_url)  # Follow the redirect to establish the session

        return session

def create_worksheets(spreadsheet):
    for ws_name in ["hep", "vio", "gpz", "a1"]:
        if ws_name not in [ws.title for ws in spreadsheet.worksheets()]:
            spreadsheet.add_worksheet(title=ws_name, rows="100", cols="100")
            print(f"Worksheet '{ws_name}' izrađen.")

def process_request(korisnicko_ime, lozinka, stranica, request_id):
    try:
        session_data = prijava(korisnicko_ime, lozinka, stranica)
        if session_data is None:
            update_status(request_id, 'Error: Login failed.', False)
            return

        session = session_data if stranica != 'hep' else session_data[0]
        kupac_id = session_data[1] if stranica == 'hep' else None

        gc = gspread.service_account(filename='api_keys/racuni.json')
        spreadsheet = gc.open("Računi")

        create_worksheets(spreadsheet)
        worksheet = spreadsheet.worksheet(stranica)

        if worksheet is None:
            update_status(request_id, 'Error: Worksheet "{}" not found or created.'.format(stranica), False)
            return

        if stranica == 'vio':
            dohvati_podatke_vio(session, worksheet)
        elif stranica == 'hep':
            dohvati_podatke_hep(session, worksheet, kupac_id)
        elif stranica == 'gpz':
            dohvati_podatke_gpz(session, worksheet)
        elif stranica == 'a1':
            dohvati_podatke_a1(session, worksheet)

        update_status(request_id, 'Data successfully written to Google Sheets - Worksheet: {}'.format(stranica), True)

    except Exception as e:
        update_status(request_id, 'Error collecting data: {}'.format(str(e)), False)

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
    app.run(debug=False)
