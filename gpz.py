from datetime import datetime
from bs4 import BeautifulSoup

def dohvati_podatke_gpz(session, worksheet):
    #dohvati HTML iz sesije
    data_url = 'https://mojracun.gpz-opskrba.hr/promet.aspx'
    response = session.get(data_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    #dohvati sve <tr> elemente koji sadrže podatke o računima
    svi_racuni = soup.find_all('tr')
    svi_racuni = [racun for racun in svi_racuni if 'FAKTURA' in racun.get_text() or 'UPLATA' in racun.get_text()]

    def get_date(racun):
        #dohvati datum iz računa
        date_string = racun.find_all('td')[0].get_text()
        return datetime.strptime(date_string, '%d.%m.%Y')

    #sortiraj račune po datumu
    svi_racuni.sort(key=get_date, reverse=True)

    #dodaj zaglavlje ako je radni list prazan
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Iznos uplate']
        worksheet.append_row(header_row)

    #dohvati datum posljednjeg unosa u radni list
    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%Y")
        #filtriraj račune koji su noviji od posljednjeg unosa
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun.find_all('td')[0].get_text(), "%d.%m.%Y") > latest_date_sheet]

    if not svi_racuni:
        return 'Nema novih računa.', True
        
    data_to_insert = []
    for racun in svi_racuni:
        datum, vrsta, iznos_racuna, iznos_uplate = extract_racun_data(racun)
        if datum:  #osiguraj da se dodaju samo valjani podaci
            data_to_insert.append([datum, vrsta, iznos_racuna, iznos_uplate])
    
    #sortiraj podatke prema datumu prije umetanja u Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"), reverse=True)

    #umetni sve podatke odjednom
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')

    return 'Podaci uspješno uneseni u radni list', True

def extract_racun_data(racun):
    #izvuci podatke iz svake kolone
    datum = racun.find_all('td')[0].get_text(strip=True)
    vrsta = racun.find_all('td')[1].get_text(strip=True)
    iznos_racuna = racun.find_all('td')[2].get_text(strip=True) if vrsta == 'FAKTURA' else ""
    iznos_uplate = racun.find_all('td')[3].get_text(strip=True) if vrsta == 'UPLATA' else ""

    vrsta = 'FAKTURA' if 'FAKTURA' in vrsta else 'UPLATA'

    return datum, vrsta, iznos_racuna, iznos_uplate
