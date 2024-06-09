from datetime import datetime
import random
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Initialize Google Drive API credentials
scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'api_keys/drive.json'
parent_folder_id = "17WYhCuwD_HkIkmNWcJJTOvDSc0d577vE"

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

def dohvati_podatke_hep(session, worksheet, kupac_id):
    # Fetch data from the new endpoint
    data_url = f'https://mojracun.hep.hr/elektra/api/promet/{kupac_id}'
    response = session.get(data_url)

    print(f"HEP data fetch response: {response.status_code}, {response.content[:200]}...")  # Print the response status and a snippet of the content

    try:
        data = response.json()
    except ValueError:
        print("Failed to parse HEP data.")
        return 'Failed to parse HEP data.', False

    svi_racuni = data.get('promet_lista', [])
    print(f"Total invoices fetched: {len(svi_racuni)}")  # Print the total number of invoices fetched

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum računa', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%y")
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun['Datum'][:10], "%Y-%m-%d") > latest_date_sheet]
        print(f"Invoices after filtering by date: {len(svi_racuni)}")  # Print the number of invoices after filtering

    data_to_insert = []
    pdf_links = {}
    for racun in svi_racuni:
        datum_racuna = racun['Datum'][:10]
        vrsta = racun['Opis']
        iznos_racuna = racun.get('Duguje', '') if racun.get('Duguje') != 0 else ''
        iznos_uplate = racun.get('Potrazuje', '') if racun.get('Potrazuje') != 0 else ''
        racun_id = racun.get('RacunId')

        if datum_racuna and racun_id:
            datum_formatted = datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%d.%m.%y")
            pdf_link = fetch_and_upload_pdf(session, kupac_id, racun_id, datum_formatted)
            data_to_insert.append([datum_formatted, vrsta, iznos_racuna, iznos_uplate, pdf_link])

    # Print the data to be inserted
    print(f"Data to insert: {data_to_insert}")

    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
        return 'Data successfully inserted into the worksheet', True

    return 'No new data to insert', True

def fetch_and_upload_pdf(session, kupac_id, racun_id, datum):
    pdf_url = 'https://mojracun.hep.hr/elektra/api/report/racun'
    payload = {
        'kupacId': kupac_id,
        'racunId': racun_id,
        'time': random.random()  # Dynamically generate a random float between 0 and 1
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

            print(f"{datum}, {pdf_filename} - Datoteka uspješno učitana.")
            return file['webViewLink']  # Return the Google Drive link
        except Exception as e:
            print(f"Pogreška prilikom učitavanja datoteke na Google Drive: {e}")
            return ""  # In case of error, return an empty link
    else:
        print(f"Pogreška prilikom preuzimanja PDF-a: {response.status_code}")
        print(f"URL: {pdf_url}")
        return ""  # In case of error, return an empty link
