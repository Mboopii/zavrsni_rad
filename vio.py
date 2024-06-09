import threading
from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests
import io

scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'api_keys/drive.json'
parent_folder_id = "1THhhwZKmJwFgtT6owYaEB7c1K31PANnU"

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

import requests
from datetime import datetime
from bs4 import BeautifulSoup

def dohvati_podatke_vio(session, worksheet):
    data_url = 'https://www.vio.hr/mojvio/racuni'
    response = session.get(data_url)

    if response.status_code != 200:
        return 'Failed to fetch data from VIO. The site may be undergoing maintenance.', False

    soup = BeautifulSoup(response.content, 'html.parser')
    invoices = soup.find_all('div', class_='invoice-class')  # Adjust the selector based on actual HTML

    if not invoices:
        return 'No invoices found. The site may be undergoing maintenance or there may be no available invoices.', False

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Datum dospijeća', 'Link na PDF']
        worksheet.append_row(header_row)

    data_to_insert = []
    for invoice in invoices:
        datum = invoice.find('span', class_='date-class').get_text(strip=True)
        vrsta = 'Račun'
        iznos_racuna = invoice.find('span', class_='amount-class').get_text(strip=True)
        datum_dospijeca = invoice.find('span', class_='due-date-class').get_text(strip=True)
        pdf_link = invoice.find('a', class_='pdf-link-class')['href']

        if datum:
            data_to_insert.append([datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link])

    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
        return 'Data successfully inserted into the worksheet', True

    return 'No new data to insert', True

def extract_racun_data(racun):
    # Extract the data from each column
    datum = racun.find_all('td')[0].get_text(strip=True)
    datum_dospijeca = racun.find_all('td')[1].get_text(strip=True)
    opis = racun.find_all('td')[2].get_text(strip=True)
    iznos_racuna = racun.find_all('td')[3].get_text(strip=True)
    iznos_uplate = racun.find_all('td')[4].get_text(strip=True)
    
    vrsta = 'Racun' if 'Racun' in opis else 'Uplata'

    # Extract PDF link for "Racun"
    pdf_link = ""
    if vrsta == 'Racun':
        pdf_element = racun.find('td', {'style': 'text-align:center;cursor:pointer;'}).find('a')
        if pdf_element:
            pdf_link = pdf_element['href']

    return datum, datum_dospijeca, vrsta, iznos_racuna, iznos_uplate, pdf_link

def upload_pdf_to_drive(pdf_url, datum, pdf_links):
    formatted_date = datetime.strptime(datum, "%d.%m.%Y").strftime("%Y_%m_%d")
    pdf_filename = f"Racun_{formatted_date}.pdf"
    response = requests.get(pdf_url)

    service = build('drive', 'v3', credentials=creds)
    content = io.BytesIO(response.content)

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
        pdf_links[pdf_url] = file['webViewLink']  # Map original URL to Google Drive link
    except Exception as e:
        print(f"Pogreška prilikom učitavanja datoteke na Google Drive: {e}")
        pdf_links[pdf_url] = ""  # In case of error, return an empty link
