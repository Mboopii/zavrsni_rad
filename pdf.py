import os
import re
import fitz
from flask import Blueprint, request, jsonify

#kreiranje blueprint-a za PDF rute
pdf_bp=Blueprint('pdf', __name__)

#osiguraj da direktorij za prijenos datoteka postoji
def ensure_upload_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

#ekstrakcija teksta iz PDF datoteke
def extract_text_from_pdf(pdf_path):
    #otvaranje PDF dokumenta
    pdf_document = fitz.open(pdf_path)
    text = ""
    #iteracija kroz sve stranice PDF-a
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()  #dohvati tekst sa stranice
    return text

#ekstrakcija podataka iz računa na temelju tipa računa
def extract_invoice_details(text, invoice_type):
    if invoice_type == 'vio':
        return extract_vio_invoice_details(text)
    elif invoice_type == 'a1':
        return extract_a1_invoice_details(text)
    elif invoice_type == 'hep':
        return extract_hep_invoice_details(text)
    else:
        return {"error": "Unsupported invoice type"}

#ekstrakcija podataka iz VIO računa
def extract_vio_invoice_details(text):
    #definiranje uzoraka za ekstrakciju podataka
    patterns = {
        "invoice_number": r"Račun\s+(\d+)",
        "invoice_period": r"za\s+vodne\s+usluge\s+i\s+naknade\s+od\s+(\d{2}\.\d{2}\.\d{4}\.)\s+do\s+(\d{2}\.\d{2}\.\d{4}\.)",
        "invoice_date": r"U Zagrebu,\s+(\d{2}\.\d{2}\.\d{4})",
        "due_date": r"Dospijeće:\s+(\d{2}\.\d{2}\.\d{4})",
        "customer_name": r"Naziv kupca:\s+([^\n]+)",  #zaustavi se na novom retku
        "amount_due": r"Iznos računa:\s+([\d,]+) EUR",
        "iban": r"\bHR\d{19}\b",  #izravno odgovara IBAN-u
    }

    details = {}
    #primjena uzoraka za pronalaženje podataka
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            if key == "invoice_period":
                details[key] = f"{matches[0][0]} to {matches[0][1]}"
            else:
                details[key] = matches[0].strip()  #ukloni nepotrebne razmake
        else:
            details[key] = None

    return details

#ekstrakcija podataka iz A1 računa
def extract_a1_invoice_details(text):
    #definiranje uzoraka za ekstrakciju podataka
    patterns = {
        "invoice_number": r"Broj računa:\s+(\d+)",
        "invoice_period": r"za razdoblje:\s+(\d{2}\.\d{2}\.\d{4}\.)\s*-\s*(\d{2}\.\d{2}\.\d{4}\.)",
        "invoice_date": r"Datum izdavanja:\s+(\d{2}\.\d{2}\.\d{4})",
        "due_date": r"Datum dospijeća:\s+(\d{2}\.\d{2}\.\d{4})",
        "customer_name": r"Platno odgovorna osoba:\s+([^,]+),\s+([^,]+),\s+([^\n]+)",  #odvoji ime i adresu
        "amount_due": r"ZA PLATITI\s+([\d,]+)",
        "iban": r"\bHR\d{19}\b",
    }

    details = {}
    #primjena uzoraka za pronalaženje podataka
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            if key == "invoice_period":
                details[key] = f"{matches[0][0]} to {matches[0][1]}"
            elif key == "customer_name":
                details["customer_name"] = matches[0][0].strip()
                details["customer_address"] = f"{matches[0][1].strip()}, {matches[0][2].strip()}"
            else:
                details[key] = matches[0].strip() if isinstance(matches[0], str) else matches[0][0].strip()
        else:
            details[key] = None

    return details

#ekstrakcija podataka iz HEP računa
def extract_hep_invoice_details(text):
    #definiranje uzoraka za ekstrakciju podataka
    patterns = {
        "invoice_number": r"Ugovorni račun:\s+(\d+)",
        "invoice_period": r"razdoblje\s+(\d{2}\.\d{2}\.\d{4})\s+-\s+(\d{2}\.\d{2}\.\d{4})",
        "invoice_date": r"Datum računa:\s+(\d{2}\.\d{2}\.\d{4})",
        "due_date": r"Datum dospijeća:\s+(\d{2}\.\d{2}\.\d{4})",
        "customer_name": r"Kupac:\s+([^\n]+)",
        "amount_due": r"UKUPAN IZNOS RAČUNA\s+([\d,]+)",
        "iban": r"\bHR\d{19}\b",  #izravno odgovara IBAN-u
    }

    details = {}
    #primjena uzoraka za pronalaženje podataka
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            if key == "invoice_period":
                details[key] = f"{matches[0][0]} to {matches[0][1]}"
            else:
                details[key] = matches[0].strip()  #ukloni nepotrebne razmake
        else:
            details[key] = None

    return details

#ruta za prijenos računa
@pdf_bp.route('/upload-invoice', methods=['POST'])
def upload_invoice():
    #provjeri postoji li datoteka u zahtjevu
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    #provjeri je li naziv datoteke prazan
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        upload_dir = 'uploads'
        #osiguraj da direktorij za prijenos datoteka postoji
        ensure_upload_directory_exists(upload_dir)
        
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)  #spremi datoteku na poslužitelj

        #ekstrakcija teksta iz PDF datoteke
        pdf_text = extract_text_from_pdf(file_path)
        invoice_type = request.form.get('invoice_type')
        
        #provjeri je li tip računa naveden
        if not invoice_type:
            return jsonify({"error": "Invoice type not provided"}), 400
        
        #ekstrakcija detalja iz računa
        invoice_details = extract_invoice_details(pdf_text, invoice_type)
        
        #ukloni PDF datoteku nakon obrade
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify(invoice_details)
