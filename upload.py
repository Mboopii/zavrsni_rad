from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import re

#inicijalizacija google drive api vjerodajnica
scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'api_keys/drive.json'

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

#funkcija za izdvajanje ID-a iz URL-a Google Drive-a
def extract_drive_id(drive_url):
    #regex za prepoznavanje google drive ID-a nakon 'folders/'
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', drive_url)
    if match:
        return match.group(1)
    else:
        return None

#funkcija za upload PDF-a na Google Drive
def upload_pdf_to_drive(session, pdf_url, datum, parent_folder_id, payload=None, date_format="%d.%m.%Y"):
    if not parent_folder_id:
        return 'Greška: Neispravan URL za Google Drive.'

    try:
        #pošalji GET ili POST zahtjev za dohvaćanje PDF-a, ovisno o tome je li payload potreban
        if payload:
            response = session.post(pdf_url, json=payload)
        else:
            response = session.get(pdf_url)

        #provjeri je li zahtjev uspješan
        if response.status_code != 200:
            return f'Neuspješno dohvaćanje PDF-a: {response.status_code}'

        #pripremi datoteku za upload na Google Drive
        formatted_datum = datetime.strptime(datum, date_format).strftime("%Y_%m_%d") if date_format == "%d.%m.%Y" else datetime.strptime(datum, date_format).strftime("%Y_%m")
        pdf_filename = f"Racun_{formatted_datum}.pdf"
        content = io.BytesIO(response.content)

        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': pdf_filename,
            'parents': [parent_folder_id]
        }

        media_body = MediaIoBaseUpload(content, mimetype='application/pdf', resumable=True)

        try:
            #upload datoteke na Google Drive
            file = service.files().create(
                body=file_metadata,
                media_body=media_body,
                fields='id, webViewLink'
            ).execute()

            print(f"Datoteka uspješno učitana na Google Drive: {file['webViewLink']}")
            return file['webViewLink']
        except Exception as e:
            print(f'Greška pri učitavanju na Google Drive: {str(e)}')
            return f'Greška pri učitavanju na Google Drive: {str(e)}'
    except Exception as e:
        return f'Greška u upload_pdf_to_drive: {str(e)}'
