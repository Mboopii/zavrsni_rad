import gspread
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from upload import extract_drive_id
from hep import dohvati_podatke_hep
from vio import dohvati_podatke_vio
from gpz import dohvati_podatke_gpz
from a1 import dohvati_podatke_a1
from google.oauth2.service_account import Credentials
from pdf import pdf_bp
import threading
import requests

#učitavanje vjerodajnica za Google API
creds = Credentials.from_service_account_file('api_keys/drive.json')

app = Flask(__name__)
CORS(app, supports_credentials=True)

#registracija PDF blueprint-a
app.register_blueprint(pdf_bp, url_prefix='/pdf')

request_lock = threading.Lock()

#funkcija za prijavu na različite stranice
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
        if response.status_code != 200:
            return None
        
        auth_token = response.json().get('Token')
        kupac_id = response.json()['Korisnik']['Kupci'][0]['KupacId']
        if auth_token:
            session.headers.update({'Authorization': f'Bearer {auth_token}'})
        else:
            return None

        return session, kupac_id

    elif stranica == 'vio':
        login_url = 'https://www.vio.hr/mojvio/?a=login'
        login_payload = {
            'email': korisnicko_ime,
            'pass': lozinka
        }
        response = session.post(login_url, data=login_payload)
        if response.status_code != 200:
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
        if response.status_code != 302:
            return None
        
        redirected_url = response.headers.get('Location')
        if redirected_url:
            response = session.get(redirected_url)
            if response.status_code != 200:
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
        if response.status_code != 302:
            return None

        #rukovanje preusmjeravanjem nakon uspješne prijave
        redirected_url = response.headers.get('Location')
        while redirected_url:
            response = session.get(redirected_url, allow_redirects=False)
            if response.status_code == 302:
                redirected_url = response.headers.get('Location')
            elif response.status_code == 200:
                return session
            else:
                return None

        return None


#funkcija za kreiranje radnih listova u Google Sheets
def create_worksheets(spreadsheet):
    for ws_name in ["hep", "vio", "gpz", "a1"]:
        if ws_name not in [ws.title for ws in spreadsheet.worksheets()]:
            spreadsheet.add_worksheet(title=ws_name, rows="100", cols="100")

#funkcija za obradu zahtjeva
def process_request(korisnicko_ime, lozinka, stranica, sheet_url, drive_url_hep, drive_url_vio, drive_url_a1):
    try:
        #prijava na odabranu stranicu
        session_data = prijava(korisnicko_ime, lozinka, stranica)
        if session_data is None:
            return 'Greška: Prijava nije uspjela.', False

        session = session_data if stranica != 'hep' else session_data[0]
        kupac_id = session_data[1] if stranica == 'hep' else None

        #ispis za debugiranje Google Sheets
        gc = gspread.service_account(filename='api_keys/racuni.json')
        try:
            spreadsheet = gc.open_by_url(sheet_url)
        except Exception:
            return f"Greška pri otvaranju Google Sheets", False
                
        create_worksheets(spreadsheet)
        
        try:
            worksheet = spreadsheet.worksheet(stranica)
        except Exception:
            return f"Greška pri otvaranju radnog lista", False
        
        if worksheet is None:
            return 'Greška: Radni list "{}" nije pronađen ili kreiran.'.format(stranica), False

        #dohvati podatke ovisno o odabranoj stranici
        if stranica == 'vio':
            result, success = dohvati_podatke_vio(session, worksheet, extract_drive_id(drive_url_vio))
        elif stranica == 'hep':
            result, success = dohvati_podatke_hep(session, worksheet, kupac_id, extract_drive_id(drive_url_hep))
        elif stranica == 'gpz':
            result, success = dohvati_podatke_gpz(session, worksheet)
        elif stranica == 'a1':
            result, success = dohvati_podatke_a1(session, worksheet, extract_drive_id(drive_url_a1))

        return result, success

    except Exception:
        return f'Greška pri prikupljanju podataka.', False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()

        korisnicko_ime = data.get('email')
        lozinka = data.get('password')
        stranica = data.get('selectedPage')
        sheet_url = data.get('sheetUrl')
        drive_url_hep = data.get('driveFolderIdHep')
        drive_url_vio = data.get('driveFolderIdVio')
        drive_url_a1 = data.get('driveFolderIdA1')

        #izravno procesiranje zahtjeva
        result, success = process_request(korisnicko_ime, lozinka, stranica, sheet_url, drive_url_hep, drive_url_vio, drive_url_a1)
        
        if success:
            return jsonify({'result': result, 'success': True}), 200
        else:
            return jsonify({'result': result, 'success': False}), 500

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False)