import requests
from datetime import datetime
from bs4 import BeautifulSoup

def dohvati_podatke_hep(session, worksheet, kupac_id):
    data_url = f'https://mojracun.hep.hr/elektra/api/racuni/kupac/{kupac_id}'
    response = session.get(data_url)

    if response.status_code != 200:
        return 'Failed to fetch data from HEP. The site may be undergoing maintenance.', False

    invoices = response.json().get('Racuni', [])
    if not invoices:
        return 'No invoices found. The site may be undergoing maintenance or there may be no available invoices.', False

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Datum dospijeća', 'Link na PDF']
        worksheet.append_row(header_row)

    data_to_insert = []
    for invoice in invoices:
        datum = invoice.get('DatumIzdavanja')
        vrsta = 'Račun'
        iznos_racuna = invoice.get('Iznos', 0)
        datum_dospijeca = invoice.get('DatumDospijeca')
        pdf_link = invoice.get('PDF')

        if datum:
            data_to_insert.append([datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link])

    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
        return 'Data successfully inserted into the worksheet', True

    return 'No new data to insert', True
