import requests
from datetime import datetime
from bs4 import BeautifulSoup

def dohvati_podatke_gpz(session, worksheet):
    data_url = 'https://mojracun.gpz-opskrba.hr/racuni'
    response = session.get(data_url)

    if response.status_code != 200:
        return 'Failed to fetch data from GPZ. The site may be undergoing maintenance.', False

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
    datum = racun.find_all('td')[0].get_text(strip=True)
    vrsta = racun.find_all('td')[1].get_text(strip=True)
    iznos_racuna = racun.find_all('td')[2].get_text(strip=True) if vrsta == 'FAKTURA' else ""
    iznos_uplate = racun.find_all('td')[3].get_text(strip=True) if vrsta == 'UPLATA' else ""

    vrsta = 'FAKTURA' if 'FAKTURA' in vrsta else 'UPLATA'

    return datum, vrsta, iznos_racuna, iznos_uplate
