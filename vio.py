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

def dohvati_podatke_vio(session, worksheet):
    # Fetch HTML from the session
    response = session.get('https://www.vio.hr/mojvio/?v=uplate')
    soup = BeautifulSoup(response.content, 'html.parser')

    # Fetch all <tr> elements containing invoice data
    svi_racuni = soup.find_all('tr')

    # Filter rows based on the presence of 'Racun' or 'Uplata' in the text
    svi_racuni = [racun for racun in svi_racuni if 'Racun' in racun.get_text() or 'Uplata' in racun.get_text()]

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Datum dospijeća', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%Y")
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun.find_all('td')[0].get_text(), "%d.%m.%Y") > latest_date_sheet]

    data_to_insert = []
    pdf_upload_threads = []
    pdf_links = {}
    for racun in reversed(svi_racuni):
        datum, datum_dospijeca, vrsta, iznos_racuna, iznos_uplate, pdf_link = extract_racun_data(racun)
        if datum:
            data_to_insert.append([datum, datum_dospijeca, vrsta, iznos_racuna, iznos_uplate, pdf_link])
            if vrsta == 'Racun' and pdf_link:
                thread = threading.Thread(target=upload_pdf_to_drive, args=(pdf_link, datum, pdf_links))
                pdf_upload_threads.append(thread)
                thread.start()
    
    # Wait for all PDF uploads to complete
    for thread in pdf_upload_threads:
        thread.join()

    # Update the data with actual Google Drive links
    for row in data_to_insert:
        if row[5] in pdf_links:
            row[5] = pdf_links[row[5]]
    
    # Sort data by date
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')

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
