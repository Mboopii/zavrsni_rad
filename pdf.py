import re
import os
import fitz
from flask import Blueprint, request, jsonify

pdf_bp = Blueprint('pdf', __name__)

def ensure_upload_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def extract_text_from_pdf(pdf_path):
    pdf_document = fitz.open(pdf_path)
    text = ""

    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()

    return text

def extract_invoice_details(text, invoice_type):
    if invoice_type == 'vio':
        return extract_vio_invoice_details(text)
    elif invoice_type == 'a1':
        return extract_a1_invoice_details(text)
    else:
        return {"error": "Unsupported invoice type"}

def extract_vio_invoice_details(text):
    patterns = {
        "invoice_number": r"Račun\s+(\d+)",
        "invoice_period": r"za\s+vodne\s+usluge\s+i\s+naknade\s+od\s+(\d{2}\.\d{2}\.\d{4}\.)\s+do\s+(\d{2}\.\d{2}\.\d{4}\.)",
        "invoice_date": r"U Zagrebu,\s+(\d{2}\.\d{2}\.\d{4})",
        "due_date": r"Dospijeće:\s+(\d{2}\.\d{2}\.\d{4})",
        "customer_name": r"Naziv kupca:\s+([^\n]+)",  # Stop at newline
        "amount_due": r"Iznos računa:\s+([\d,]+) EUR",
    }

    details = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            if key == "invoice_period":
                details[key] = f"{match.group(1)} to {match.group(2)}"
            else:
                details[key] = match.group(1).strip()
        else:
            details[key] = None

    meter_readings = []
    meter_rows = re.findall(r"(\d{2}\.\d{2}\.\d{4})\s+[O|P]\s+(\d+)\s+(\d+)\s+(\d+)", text)

    for row in meter_rows:
        date, meter_number, meter_reading, consumption = row
        meter_readings.append({
            "date": date,
            "meter_number": meter_number,
            "meter_reading": meter_reading,
            "consumption": consumption
        })

    details['meter_readings'] = meter_readings

    return details

def extract_a1_invoice_details(text):
    patterns = {
        "invoice_number": r"Broj računa:\s+(\d+)",
        "invoice_period": r"za razdoblje:\s+(\d{2}\.\d{2}\.\d{4}.)\s*-\s*(\d{2}\.\d{2}\.\d{4}.)",
        "invoice_date": r"Datum izdavanja:\s+(\d{2}\.\d{2}\.\d{4})",
        "due_date": r"Datum dospijeća:\s+(\d{2}\.\d{2}\.\d{4})",
        "customer_name": r"Platno odgovorna osoba:\s+([^,]+),\s+([^,]+),\s+([^\n]+)",  # Separate name and address
        "amount_due": r"ZA PLATITI\s+([\d,]+)",
    }

    details = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            if key == "invoice_period":
                details[key] = f"{match.group(1)} to {match.group(2)}"
            elif key == "customer_name":
                details["customer_name"] = match.group(1).strip()
                details["customer_address"] = f"{match.group(2).strip()}, {match.group(3).strip()}"
            else:
                details[key] = match.group(1).strip()
        else:
            details[key] = None

    if details['invoice_period'] is None:
        period_context = re.search(r"Račun za pružene usluge\s+za razdoblje:\s+(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})", text, re.IGNORECASE | re.DOTALL)
        if period_context:
            details["invoice_period"] = f"{period_context.group(1)} to {period_context.group(2)}"
        else:
            print("Invoice Period Debug - No context found for invoice period in text")

    return details

@pdf_bp.route('/upload-invoice', methods=['POST'])
def upload_invoice():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        upload_dir = 'uploads'
        ensure_upload_directory_exists(upload_dir)
        
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)

        pdf_text = extract_text_from_pdf(file_path)
        print("Extracted Text:\n", pdf_text)  # Debug: Print the extracted text

        invoice_type = request.form.get('invoice_type', 'vio')
        invoice_details = extract_invoice_details(pdf_text, invoice_type)
        
        print("Invoice Details:\n", invoice_details)  # Debug: Print the extracted details

        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify(invoice_details)
