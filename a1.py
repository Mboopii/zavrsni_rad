import concurrent.futures
from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests
import io

#inicijalizacija google drive api vjerodajnica
scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'api_keys/drive.json'
parent_folder_id = "1IF4YRCjxJULLJk_lQz_TbMEjwMLrzQXZ"  # Update this with your Google Drive folder ID

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

def dohvati_podatke_a1(session, worksheet):
    #dohvati html iz sesije
    data_url = 'https://moj.a1.hr/postpaid/residential/pregled-racuna'
    response = session.get(data_url)
    
    if response.status_code == 302 and "nedostupno" in response.headers.get('Location', ''):
        return 'A1 site is currently under maintenance. Please try again later.', False

    if response.status_code != 200:
        return 'Failed to fetch data from A1. The site may be undergoing maintenance.', False

    soup = BeautifulSoup(response.content, 'html.parser')

    #dohvati sve elemente koji sadrže vidljive podatke o računima
    svi_racuni = soup.find_all('div', class_='mv-Payment g-12 g-reset g-rwd p')
    if not svi_racuni:
        return 'No invoices found. The site may be undergoing maintenance or there may be no available invoices.', False

    visible_racuni = [racun for racun in svi_racuni if not is_hidden(racun)]

    #dodaj zaglavlje ako je radni list prazan
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Datum dospijeća', 'Link na PDF']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%Y")
        visible_racuni = [racun for racun in visible_racuni if extract_date(racun) > latest_date_sheet]

    data_to_insert = []
    pdf_links = {}

    def fetch_and_upload(racun):
        datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link = extract_racun_data(racun)
        if datum:
            if pdf_link:
                pdf_link = upload_pdf_to_drive(session, pdf_link, datum)
            return [datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link]
        return None

    # Asinkrono preuzimanje i upload PDF-ova
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_racun = {executor.submit(fetch_and_upload, racun): racun for racun in visible_racuni}
        for future in concurrent.futures.as_completed(future_to_racun):
            result = future.result()
            if result:
                data_to_insert.append(result)

    # Sortiraj podatke po datumu prije umetanja u google sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%m/%Y"), reverse=True)

    # Umetni sve podatke odjednom
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
        return 'Data successfully inserted into the worksheet', True

    return 'No new data to insert', True

def is_hidden(element):
    parent = element.find_parent(attrs={"class": "js-toggle-section hide"})
    return parent is not None

def extract_date(racun):
    #izvuci mjesec/godinu i pretpostavi prvi dan u mjesecu
    period_element = racun.find('div', class_='mv-Payment-period mv-Payment-infoCell mv-Payment-infoCell g-4')
    if period_element:
        date_string = period_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
        return datetime.strptime(f"{date_string}", "%m/%Y")
    return datetime.min  #vrati vrlo star datum ako nije pronađen kako bi bio isključen iz obrade

def extract_racun_data(racun):
    #izvuci podatke iz svake kolone
    period_element = racun.find('div', class_='mv-Payment-period mv-Payment-infoCell mv-Payment-infoCell g-4')
    if period_element:
        month_year = period_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
        datum = f"{month_year}"  #pretpostavi prvi dan mjeseca razdoblja naplate
    else:
        datum = ""
    
    vrsta = 'Račun'
    
    sum_element = racun.find('div', class_='mv-Payment-sum mv-Payment-infoCell mv-Payment-infoCell g-4')
    if sum_element:
        iznos_racuna = sum_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
    else:
        iznos_racuna = ""
    
    due_element = racun.find('div', class_='mv-Payment-due mv-Payment-infoCell mv-Payment-infoCell g-4')
    if due_element is None:
        due_element = racun.find('div', class_='mv-Payment-due mv-Payment-infoCell mv-Payment-infoCell g-4 is-late')
    if due_element:
        due_text_element = due_element.find('div', class_='u-fontStrong u-textCenter')
        if due_text_element:
            datum_dospijeca = due_text_element.get_text(strip=True)
        else:
            datum_dospijeca = ""
    else:
        datum_dospijeca = ""

    #kreiraj link na pdf
    pdf_link = ""
    pdf_element = racun.find('a', class_='bill_pdf_export')
    if pdf_element and pdf_element.has_attr('href'):
        pdf_link = f"https://moj.a1.hr{pdf_element['href']}"

    return datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link

def upload_pdf_to_drive(session, pdf_url, datum):
    response = session.get(pdf_url)
    if response.status_code == 200:
        formatted_date = datetime.strptime(datum, "%m/%Y").strftime("%Y_%m")
        pdf_filename = f"Racun_{formatted_date}.pdf"
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

            return file['webViewLink']  #mapiraj izvorni URL na google drive link
        except Exception as e:
            return ""  #u slučaju greške, vrati prazan link
    else:
        return ""  #u slučaju greške, vrati prazan link
