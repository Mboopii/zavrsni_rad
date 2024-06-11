import concurrent.futures
from datetime import datetime
import random
from upload import upload_pdf_to_drive, extract_drive_id

def dohvati_podatke_hep(session, worksheet, kupac_id, parent_folder_id):
    try:
        #postavi URL za dohvaćanje podataka
        data_url = f'https://mojracun.hep.hr/elektra/api/promet/{kupac_id}'
        #pošalji GET zahtjev za dohvaćanje podataka
        response = session.get(data_url)

        #provjeri je li zahtjev uspješan
        if response.status_code != 200:
            return f'Neuspješno dohvaćanje HEP podataka: {response.status_code}', False

        try:
            #parsiranje JSON odgovora
            data = response.json()
        except ValueError as e:
            return f'Neuspješno parsiranje HEP podataka: {str(e)}', False

        #dohvati sve računeS
        svi_racuni = data.get('promet_lista', [])

        #ako je radni list prazan, dodaj zaglavlje
        if not worksheet.get_all_values():
            header_row = ['Datum računa', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF']
            worksheet.append_row(header_row)

        #dohvati datum posljednjeg unosa u radni list
        latest_date_sheet = worksheet.cell(2, 1).value
        if latest_date_sheet:
            latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%y")
            #filtriraj račune koji su noviji od posljednjeg unosa
            svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun['Datum'][:10], "%Y-%m-%d") > latest_date_sheet]

        if not svi_racuni:
            return 'Nema novih računa.', True
        
        data_to_insert = []

        def fetch_and_upload(racun):
            datum_racuna = racun['Datum'][:10]
            vrsta = racun['Opis']
            iznos_racuna = racun.get('Duguje', '') if racun.get('Duguje') != 0 else ''
            iznos_uplate = racun.get('Potrazuje', '') if racun.get('Potrazuje') != 0 else ''
            racun_id = racun.get('Racun')

            datum_formatted = datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%d.%m.%Y")
            pdf_link = ""
            if vrsta == 'Račun' and racun_id:
                #postavi URL za dohvaćanje PDF-a
                pdf_url = 'https://mojracun.hep.hr/elektra/api/report/racun'
                payload = {
                    'kupacId': kupac_id,
                    'racunId': racun_id,
                    'time': random.random()
                }
                #upload PDF-a na Google Drive
                pdf_link = upload_pdf_to_drive(session, pdf_url, datum_formatted, parent_folder_id, payload)
            return [datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%d.%m.%y"), vrsta, iznos_racuna, iznos_uplate, pdf_link]

        #paralelno dohvaćanje i upload podataka
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_racun = {executor.submit(fetch_and_upload, racun): racun for racun in svi_racuni}
            for future in concurrent.futures.as_completed(future_to_racun):
                data_to_insert.append(future.result())

        #sortiraj podatke prema datumu
        data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%y"), reverse=True)

        #unesi podatke u radni list
        if data_to_insert:
            worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
            return 'Podaci uspješno uneseni u radni list', True

        return 'Nema novih podataka za unos', True
    except Exception as e:
        return f'Greška pri dohvaćanju hep računa', False