from datetime import datetime

def dohvati_podatke_hep(session, worksheet, kupac_id):
    # Fetch data from the new endpoint
    data_url = f'https://mojracun.hep.hr/elektra/api/promet/{kupac_id}'
    response = session.get(data_url)
    
    try:
        data = response.json()
    except ValueError:
        return

    svi_racuni = data.get('promet_lista', [])

    # Add header if the worksheet is empty
    if not worksheet.get_all_values():
        header_row = ['Datum računa', 'Vrsta', 'Iznos računa', 'Iznos uplate']
        worksheet.append_row(header_row)

    latest_date_sheet = worksheet.cell(2, 1).value
    if latest_date_sheet:
        latest_date_sheet = datetime.strptime(latest_date_sheet, "%d.%m.%y")
        svi_racuni = [racun for racun in svi_racuni if datetime.strptime(racun['Datum'][:10], "%Y-%m-%d") > latest_date_sheet]

    data_to_insert = []
    for racun in svi_racuni:
        datum_racuna = racun['Datum'][:10]
        vrsta = racun['Opis']
        iznos_racuna = racun.get('Duguje', '') if racun.get('Duguje') != 0 else ''
        iznos_uplate = racun.get('Potrazuje', '') if racun.get('Potrazuje') != 0 else ''

        if datum_racuna:
            data_to_insert.append([datetime.strptime(datum_racuna, "%Y-%m-%d").strftime("%d.%m.%y"), vrsta, iznos_racuna, iznos_uplate])

    # Sort data by date before inserting into Google Sheets
    data_to_insert.sort(key=lambda x: datetime.strptime(x[0], "%d.%m.%y"), reverse=True)

    # Insert all data at once
    if data_to_insert:
        worksheet.insert_rows(data_to_insert, 2, value_input_option='RAW')
