from datetime import datetime
from bs4 import BeautifulSoup
import requests

def dohvati_podatke_gpz(session, worksheet):
    # Fetch HTML from the session
    data_url = 'https://mojracun.gpz-opskrba.hr/promet.aspx'
    response = session.get(data_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Fetch all <tr> elements containing invoice data
    svi_racuni = soup.find_all('tr')
    svi_racuni = [racun for racun in svi_racuni if 'FAKTURA' in racun.get_text() or 'UPLATA' in racun.get_text()]

    def get_date(racun):
        date_string = racun.find_all('td')[0].get_text()
        return datetime.strptime(date_string, '%d.%m.%Y')

    svi_racuni.sort(key=get_date, reverse=True)

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Iznos uplate']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%Y")
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun.find_all('td')[0].get_text(), "%d.%m.%Y") > latest_date_sheet]

    data_to_insert = []
    for racun in svi_racuni:
        datum, vrsta, iznos_racuna, iznos_uplate = extract_racun_data(racun)
        if datum:  # Ensure valid data is being added
            data_to_insert.append([datum, vrsta, iznos_racuna, iznos_uplate])
    
    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')

def extract_racun_data(racun):
    datum = racun.find_all('td')[0].get_text(strip=True)
    vrsta = racun.find_all('td')[1].get_text(strip=True)
    iznos_racuna = racun.find_all('td')[2].get_text(strip=True) if vrsta == 'FAKTURA' else ""
    iznos_uplate = racun.find_all('td')[3].get_text(strip=True) if vrsta == 'UPLATA' else ""

    vrsta = 'FAKTURA' if 'FAKTURA' in vrsta else 'UPLATA'

    return datum, vrsta, iznos_racuna, iznos_uplate
