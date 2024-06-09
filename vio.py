import threading
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests
import io
import random

#inicijalizacija google drive api vjerodajnica
scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'api_keys/drive.json'
parent_folder_id = "17WYhCuwD_HkIkmNWcJJTOvDSc0d577vE"

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

def dohvati_podatke_hep(session, worksheet, kupac_id):
    #dohvati podatke s novog krajnjeg točka
    data_url = f'https://mojracun.hep.hr/elektra/api/promet/{kupac_id}'
    response = session.get(data_url)

    try:
        data = response.json()
    except ValueError:
        return 'Neuspjelo parsiranje HEP podataka.', False

    svi_racuni = data.get('promet_lista', [])

    #dodaj zaglavlje ako je radni list prazan
    if not worksheet.get_all_values():
        header_row = ['Datum računa', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%y")
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun['Datum'][:10], "%Y-%m-%d") > latest_date_sheet]

    data_to_insert = []
    pdf_upload_threads = []
    pdf_links = {}
    for racun in svi_racuni:
        datum_racuna = racun['Datum'][:10]
        vrsta = racun['Opis']
        iznos_racuna = racun.get('Duguje', '') if racun.get('Duguje') != 0 else ''
        iznos_uplate = racun.get('Potrazuje', '') if racun.get('Potrazuje') != 0 else ''
        racun_id = racun.get('Racun')

        if datum_racuna:
            datum_formatted = datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%d.%m.%y")
            pdf_link = ""
            if racun_id:
                thread = threading.Thread(target=upload_pdf_to_drive, args=(session, kupac_id, racun_id, datum_formatted, pdf_links))
                pdf_upload_threads.append(thread)
                thread.start()
            data_to_insert.append([datum_formatted, vrsta, iznos_racuna, iznos_uplate, racun_id])

    #čekaj da se svi PDF-ovi učitaju
    for thread in pdf_upload_threads:
        thread.join()

    #ažuriraj podatke s pravim linkovima na google drive
    for row in data_to_insert:
        if row[4] in pdf_links:
            row[4] = pdf_links[row[4]]
        else:
            row[4] = ""  #ako nema PDF linka, postavi prazno polje
    
    #sortiraj podatke po datumu prije umetanja u google sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%y"), reverse=True)

    #umetni sve podatke odjednom
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
        return 'Podaci uspješno umetnuti u radni list', True

    return 'Nema novih podataka za umetanje', True

def upload_pdf_to_drive(session, kupac_id, racun_id, datum, pdf_links):
    pdf_url = 'https://mojracun.hep.hr/elektra/api/report/racun'
    payload = {
        'kupacId': kupac_id,
        'racunId': racun_id,
        'time': random.random()  #dinamički generiraj slučajni float između 0 i 1
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = session.post(pdf_url, json=payload, headers=headers)

    if response.status_code == 200:
        pdf_filename = f"Racun_{datum}.pdf"
        content = io.BytesIO(response.content)

        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': pdf_filename,
            'parents': [parent_folder_id]
        }

        media_body = MediaIoBaseUpload(content, mimetype='application/pdf', resumable=True)

        try:
            file = service.files().create(
                body=file_metadata,
                media_body=media_body,
                fields='id, webViewLink'
            ).execute()

            pdf_links[racun_id] = file['webViewLink']  #mapiraj racun_id na google drive link
        except Exception as e:
            pdf_links[racun_id] = ""  #u slučaju greške, vrati prazan link
    else:
        pdf_links[racun_id] = ""  #u slučaju greške, vrati prazan link
