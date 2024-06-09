import threading
from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests
import io

# Initialize Google Drive API credentials
scopes = ['https://www.googleapis.com/auth/drive']
service_account_file = 'api_keys/drive.json'
parent_folder_id = "1IF4YRCjxJULLJk_lQz_TbMEjwMLrzQXZ"  # Update this with your Google Drive folder ID

creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)

def dohvati_podatke_a1(driver, worksheet):
    # Create a session to maintain cookies
    session = requests.Session()

    # Extract cookies from the driver and add them to the session
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    # Fetch HTML from webdriver
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Fetch all elements containing visible invoice data
    svi_racuni = soup.find_all('div', class_='mv-Payment g-12 g-reset g-rwd p')
    visible_racuni = [racun for racun in svi_racuni if not is_hidden(racun)]

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Datum dospijeća', 'Link na PDF']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%Y")
        visible_racuni = [racun for racun in visible_racuni if extract_date(racun) > latest_date_sheet]

    data_to_insert = []
    pdf_upload_threads = []
    pdf_links = {}
    for racun in visible_racuni:
        datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link = extract_racun_data(racun)
        if datum:
            data_to_insert.append([datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link])
            if pdf_link:
                thread = threading.Thread(target=upload_pdf_to_drive, args=(session, pdf_link, datum, pdf_links))
                pdf_upload_threads.append(thread)
                thread.start()
    
    # Wait for all PDF uploads to complete
    for thread in pdf_upload_threads:
        thread.join()

    # Update the data with actual Google Drive links
    for row in data_to_insert:
        if row[4] in pdf_links:
            row[4] = pdf_links[row[4]]
    
    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%m/%Y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')

def is_hidden(element):
    parent = element.find_parent(attrs={"class": "js-toggle-section hide"})
    return parent is not None

def extract_date(racun):
    # Extract the month/year and assume the first day of the month
    period_element = racun.find('div', class_='mv-Payment-period mv-Payment-infoCell mv-Payment-infoCell g-4')
    if period_element:
        date_string = period_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
        return datetime.strptime(f"{date_string}", "%m/%Y")
    return datetime.min  # Return a very old date if not found to exclude from processing

def extract_racun_data(racun):
    # Extract the data from each column
    period_element = racun.find('div', class_='mv-Payment-period mv-Payment-infoCell mv-Payment-infoCell g-4')
    if period_element:
        month_year = period_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
        datum = f"{month_year}"  # Assume the first day of the billing period month
        month, year = month_year.split('/')
    else:
        datum = ""
        year, month = "", ""
    
    vrsta = 'Račun'
    
    sum_element = racun.find('div', class_='mv-Payment-sum mv-Payment-infoCell mv-Payment-infoCell g-4')
    if sum_element:
        iznos_racuna = sum_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
    else:
        iznos_racuna = ""
    
    due_element = racun.find('div', class_='mv-Payment-due mv-Payment-infoCell mv-Payment-infoCell g-4')
    if due_element:
        datum_dospijeca = due_element.find('div', class_='u-fontStrong u-textCenter').get_text(strip=True)
    else:
        datum_dospijeca = ""

    # Construct the PDF link
    if year and month:
        pdf_link = f"https://moj.a1.hr/postpaid/residential/pregled-racuna?p_p_id=monthlycost_WAR_moja1postpaidportlets&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getPdfDocument&p_p_cacheability=cacheLevelPage&_monthlycost_WAR_moja1postpaidportlets_date={year}-{month}"
    else:
        pdf_link = ""

    return datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link

def upload_pdf_to_drive(session, pdf_url, datum, pdf_links):
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

            print(f"{datum}, {pdf_filename} - Datoteka uspješno učitana.")
            pdf_links[pdf_url] = file['webViewLink']  # Map original URL to Google Drive link
        except Exception as e:
            print(f"Pogreška prilikom učitavanja datoteke na Google Drive: {e}")
            pdf_links[pdf_url] = ""  # In case of error, return an empty link
    else:
        print(f"Pogreška prilikom preuzimanja PDF-a: {response.status_code}")
        print(f"URL: {pdf_url}")
        pdf_links[pdf_url] = ""  # In case of error, return an empty link
