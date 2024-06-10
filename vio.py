import concurrent.futures
from datetime import datetime
from bs4 import BeautifulSoup
from upload import upload_pdf_to_drive, extract_drive_id

def dohvati_podatke_vio(session, worksheet, parent_folder_id):
    #pošalji GET zahtjev za dohvaćanje podataka
    response = session.get('https://www.vio.hr/mojvio/?v=uplate')
    #parsiranje HTML odgovora
    soup = BeautifulSoup(response.content, 'html.parser')

    #dohvati sve redove s podacima o računima
    svi_racuni = soup.find_all('tr')
    svi_racuni = [racun for racun in svi_racuni if 'Racun' in racun.get_text() or 'Uplata' in racun.get_text()]

    #ako je radni list prazan, dodaj zaglavlje
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Datum dospijeća', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF']
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

    def fetch_and_upload(racun):
        datum, datum_dospijeca, vrsta, iznos_racuna, iznos_uplate, pdf_link = extract_racun_data(racun)
        if vrsta == 'Racun' and pdf_link:
            pdf_link = upload_pdf_to_drive(session, pdf_link, datum, parent_folder_id)
        return [datum, datum_dospijeca, vrsta, iznos_racuna, iznos_uplate, pdf_link]

    #paralelno dohvaćanje i upload podataka
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_racun = {executor.submit(fetch_and_upload, racun): racun for racun in svi_racuni}
        for future in concurrent.futures.as_completed(future_to_racun):
            data_to_insert.append(future.result())

    #sortiraj podatke prema datumu
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"), reverse=True)

    #umetni sve podatke odjednom
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')

    return 'Podaci uspješno uneseni u radni list', True

def extract_racun_data(racun):
    #izvuci podatke iz svake kolone
    datum = racun.find_all('td')[0].get_text(strip=True)
    datum_dospijeca = racun.find_all('td')[1].get_text(strip=True)
    opis = racun.find_all('td')[2].get_text(strip=True)
    iznos_racuna = racun.find_all('td')[3].get_text(strip=True)
    iznos_uplate = racun.find_all('td')[4].get_text(strip=True)
    
    vrsta = 'Racun' if 'Racun' in opis else 'Uplata'

    #izvuci pdf link za 'Racun'
    pdf_link = ""
    if vrsta == 'Racun':
        pdf_element = racun.find('td', {'style': 'text-align:center;cursor:pointer;'}).find('a')
        if pdf_element:
            pdf_link = pdf_element['href']

    return datum, datum_dospijeca, vrsta, iznos_racuna, iznos_uplate, pdf_link
