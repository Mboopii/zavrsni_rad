import threading
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from upload import upload_pdf_to_drive, extract_drive_id

def dohvati_podatke_a1(session, worksheet, parent_folder_id):
    #dohvati html iz sesije
    data_url = 'https://moj.a1.hr/postpaid/residential/pregled-racuna'
    response = session.get(data_url)
    
    if response.status_code == 302 and "nedostupno" in response.headers.get('Location', ''):
        return 'A1 stranica trenutno nije dostupna. Molimo pokušajte kasnije.', False

    if response.status_code != 200:
        return 'Neuspješno dohvaćanje podataka s A1. Stranica može biti u održavanju.', False

    soup = BeautifulSoup(response.content, 'html.parser')

    #dohvati sve elemente koji sadrže vidljive podatke o računima
    svi_racuni = soup.find_all('div', class_='mv-Payment g-12 g-reset g-rwd p')
    if not svi_racuni:
        return 'Nema pronađenih računa. Stranica može biti u održavanju ili nema dostupnih računa.', False

    visible_racuni = [racun for racun in svi_racuni if not is_hidden(racun)]

    #dodaj zaglavlje ako je radni list prazan
    if not worksheet.get_all_values():
        header_row = ['Datum', 'Vrsta', 'Iznos računa', 'Datum dospijeća', 'Link na PDF']
        worksheet.append_row(header_row)

    #dohvati datum posljednjeg unosa u radni list
    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%m/%Y")
        visible_racuni = [racun for racun in visible_racuni if extract_date(racun) > latest_date_sheet]

    if not visible_racuni:
        return 'Nema novih računa.', True
    
    data_to_insert = []
    pdf_links = {}
    threads = []

    def fetch_and_upload(racun):
        datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link = extract_racun_data(racun)
        if datum:
            if pdf_link:
                pdf_link = upload_pdf_to_drive(session, pdf_link, datum, parent_folder_id, date_format="%m/%Y")
            data_to_insert.append([datum, vrsta, iznos_racuna, datum_dospijeca, pdf_link])

    #paralelno preuzimanje i upload PDF-ova
    for racun in visible_racuni:
        thread = threading.Thread(target=fetch_and_upload, args=(racun,))
        threads.append(thread)
        thread.start()

    #pričekaj završetak svih niti
    for thread in threads:
        thread.join()

    #sortiraj podatke po datumu prije umetanja u google sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%m/%Y"), reverse=True)

    #umetni sve podatke odjednom
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
        return 'Podaci uspješno uneseni u radni list', True

    return 'Nema novih podataka za unos', True

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
