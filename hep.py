import concurrent.futures
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

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

def dohvati_podatke_hep(session, worksheet, kupac_id, parent_folder_id):
    try:
        data_url = f'https://mojracun.hep.hr/elektra/api/promet/{kupac_id}'
        response = session.get(data_url)

        if response.status_code != 200:
            return f'Failed to fetch HEP data: {response.status_code}', False

        try:
            data = response.json()
        except ValueError as e:
            return f'Failed to parse HEP data: {str(e)}', False

        svi_racuni = data.get('promet_lista', [])

        if not worksheet.get_all_values():
            header_row = ['Datum računa', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF']
            worksheet.append_row(header_row)

        latest_date_sheet = worksheet.cell(2, 1).value
        if latest_date_sheet:
            latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%y")
            svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun['Datum'][:10], "%Y-%m-%d") > latest_date_sheet]

        data_to_insert = []
        pdf_links = {}

        def fetch_and_upload(racun):
            datum_racuna = racun['Datum'][:10]
            vrsta = racun['Opis']
            iznos_racuna = racun.get('Duguje', '') if racun.get('Duguje') != 0 else ''
            iznos_uplate = racun.get('Potrazuje', '') if racun.get('Potrazuje') != 0 else ''
            racun_id = racun.get('Racun')

            datum_formatted = datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%Y_%m_%d")
            pdf_link = ""
            if vrsta == 'Račun' and racun_id:
                pdf_url = 'https://mojracun.hep.hr/elektra/api/report/racun'
                payload = {
                    'kupacId': kupac_id,
                    'racunId': racun_id,
                    'time': random.random()
                }
                headers = {
                    'Content-Type': 'application/json'
                }
                pdf_link = upload_pdf_to_drive(session, pdf_url, payload, datum_formatted, parent_folder_id)

            return [datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%d.%m.%y"), vrsta, iznos_racuna, iznos_uplate, pdf_link]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_racun = {executor.submit(fetch_and_upload, racun): racun for racun in svi_racuni}
            for future in concurrent.futures.as_completed(future_to_racun):
                data_to_insert.append(future.result())

        data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%y"), reverse=True)

        if data_to_insert:
            worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
            return 'Data successfully inserted into the worksheet', True

        return 'No new data to insert', True
    except Exception as e:
        return f'Error in dohvati_podatke_hep: {str(e)}', False

def upload_pdf_to_drive(session, pdf_url, payload, datum, parent_folder_id):
    try:
        response = session.post(pdf_url, json=payload)

        if response.status_code != 200:
            return f'Failed to fetch PDF: {response.status_code}'

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

            return file['webViewLink']
        except Exception as e:
            return f'Error uploading to Google Drive: {str(e)}'
    except Exception as e:
        return f'Error in upload_pdf_to_drive: {str(e)}'
