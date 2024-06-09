from datetime import datetime
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

def dohvati_podatke_hep(driver, worksheet):
    # Dohvati HTML
    soup_promet = BeautifulSoup(driver.page_source, 'html.parser')

    # Dohvati sve <tr> elemente koji sadrže podatke o računu
    svi_racuni = soup_promet.find_all('tr', {'ng-repeat-start': 'p in promet track by $index'})

    # Svaki red rasporedi po tipu računa/uplate (Račun, Uplaćeno, Akontacija)
    svi_racuni = [racun for racun in svi_racuni if 'Račun' in racun.get_text() or 'Uplaćeno' in racun.get_text() or 'Akontacija' in racun.get_text()]

    # Ako je radni list prazan, dodaj zaglavlje
    if not worksheet.get_all_values():
        header_row = ['Datum računa', 'Vrsta', 'Iznos računa', 'Datum uplate', 'Iznos uplate']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%y")
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun.find('td', class_='ng-binding').get_text(), "%d.%m.%y") > latest_date_sheet]

    data_to_insert = []
    for racun in svi_racuni:
        datum_racuna, iznos_racuna, datum_uplate, iznos_uplate, vrsta = extract_racun_data(racun)
        if datum_racuna:  # Ensure valid data is being added
            data_to_insert.append([datum_racuna, vrsta, iznos_racuna, datum_uplate, iznos_uplate])
    
    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')

def extract_racun_data(racun):
    datum_str = racun.find_all('td', class_='ng-binding')[0].get_text()
    vrsta = racun.find_all('td', class_='ng-binding')[1].get_text()

    iznos_racuna = ""
    datum_uplate = ""
    iznos_uplate = ""

    if vrsta == 'Račun':
        iznos_racuna_element = racun.find_all('td')[2].find('span', class_='ng-binding')
        iznos_racuna = iznos_racuna_element.get_text(strip=True) if iznos_racuna_element else ""
    elif vrsta == 'Uplaćeno':
        iznos_uplate_element = racun.find_all('td')[3].find('span', class_='ng-binding')
        iznos_uplate = iznos_uplate_element.get_text(strip=True) if iznos_uplate_element else "0,00"
        datum_uplate = datum_str
    elif vrsta == 'Akontacija':
        iznos_racuna_element = racun.find_all('td')[2].find('span', class_='ng-binding')
        iznos_racuna = iznos_racuna_element.get_text(strip=True) if iznos_racuna_element else ""

    return datum_str, iznos_racuna, datum_uplate, iznos_uplate, vrsta
