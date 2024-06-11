//funkcija za obradu slanja forme za popis računa
async function submitForm(event) {
    event.preventDefault(); //sprječavanje zadane akcije slanja forme

    //dohvaćanje vrijednosti iz forme
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const selectedPage = document.getElementById('page').value;
    const sheetUrl = document.getElementById('sheetUrl').value;
    const driveFolderIdHep = document.getElementById('driveFolderIdHep').value;
    const driveFolderIdVio = document.getElementById('driveFolderIdVio').value;
    const driveFolderIdA1 = document.getElementById('driveFolderIdA1').value;

    //prikazivanje loadera
    document.getElementById('loader').style.display = 'block';
    document.querySelector('.loader-background').style.display = 'block';

    try {
        //slanje POST zahtjeva s podacima forme
        const response = await fetch('/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password,
                selectedPage,
                sheetUrl,
                driveFolderIdHep,
                driveFolderIdVio,
                driveFolderIdA1
            }),
        });

        //provjera je li zahtjev uspješan
        if (response.ok) {
            const data = await response.json();
            document.getElementById('result').innerText = data.result;

            //brisanje vrijednosti polja za Google Drive ID nakon uspješnog slanja
            document.getElementById('driveFolderIdHep').value = '';
            document.getElementById('driveFolderIdVio').value = '';
            document.getElementById('driveFolderIdA1').value = '';
        } else {
            //obrada greške pri neuspješnom zahtjevu
            const errorData = await response.json();
            document.getElementById('result').innerText = errorData.result || 'Greška pri prikupljanju podataka.';
        }
    } catch (error) {
        console.error("Greška: ", error); //ispis greške u konzolu
        document.getElementById('result').innerText = 'Došlo je do greške prilikom slanja zahtjeva.';
    } finally {
        //sakrivanje loadera
        document.getElementById('loader').style.display = 'none';
        document.querySelector('.loader-background').style.display = 'none';
    }
}

//funkcija za prikazivanje/skrivanje polja za Google Drive ID ovisno o odabranoj stranici
function toggleDriveFolderId() {
    const page = document.getElementById('page').value;
    document.getElementById('driveFolderIdHepContainer').style.display = page === 'hep' ? 'block' : 'none';
    document.getElementById('driveFolderIdVioContainer').style.display = page === 'vio' ? 'block' : 'none';
    document.getElementById('driveFolderIdA1Container').style.display = page === 'a1' ? 'block' : 'none';
}

async function submitPdfForm(event) {
    event.preventDefault();

    const form = document.getElementById('pdfForm');
    const formData = new FormData(form);

    document.getElementById('loader').style.display = 'block';
    document.querySelector('.loader-background').style.display = 'block';

    try {
        const response = await fetch('http://127.0.0.1:5000/pdf/upload-invoice', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            const orderedKeys = [
                'invoice_number', 'customer_name', 'iban', 'invoice_date', 'due_date',
                'amount_due', 'total_amount', 'invoice_period', 'meter_readings'
            ];
            const croatianKeys = {
                'invoice_number': 'BROJ RAČUNA',
                'customer_name': 'IME KUPCA',
                'iban': 'IBAN',
                'invoice_date': 'DATUM RAČUNA',
                'due_date': 'DATUM DOSPIJEĆA',
                'amount_due': 'IZNOS ZA UPLATU',
                'total_amount': 'UKUPAN IZNOS',
                'invoice_period': 'RAZDOBLJE RAČUNA',
                'meter_readings': 'OČITANJA BROJILA'
            };
            let resultHtml = '<table class="table table-bordered">';
            orderedKeys.forEach(key => {
                if (data[key] !== undefined) {
                    if (key === 'meter_readings') {
                        resultHtml += `<tr><td colspan="2"><strong>${croatianKeys[key]}</strong></td></tr>`;
                        resultHtml += `<tr><td colspan="2"><table class="table table-bordered"><thead><tr><th>DATUM</th><th>BROJ BROJILA</th><th>OČITANJE BROJILA</th><th>POTROŠNJA</th></tr></thead><tbody>`;
                        data[key].forEach(reading => {
                            resultHtml += `
                                <tr>
                                    <td>${reading.date}</td>
                                    <td>${reading.meter_number}</td>
                                    <td>${reading.meter_reading}</td>
                                    <td>${reading.consumption}</td>
                                </tr>
                            `;
                        });
                        resultHtml += '</tbody></table></td></tr>';
                    } else {
                        resultHtml += `<tr><td><strong>${croatianKeys[key]}:</strong></td><td>${data[key]}</td></tr>`;
                    }
                }
            });
            resultHtml += '</table>';
            document.getElementById('pdf-result').innerHTML = resultHtml;

            form.reset();
            document.getElementById('invoiceType').selectedIndex = 0;
        } else {
            document.getElementById('pdf-result').innerText = 'Greška pri učitavanju PDF-a.';
        }
    } catch (error) {
        console.error("Greška: ", error);
        document.getElementById('pdf-result').innerText = 'Greška pri učitavanju PDF-a.';
    } finally {
        document.getElementById('loader').style.display = 'none';
        document.querySelector('.loader-background').style.display = 'none';
    }
}

//dodavanje event listenera za slanje formi i promjene odabira stranice
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginForm').addEventListener('submit', submitForm);
    document.getElementById('pdfForm').addEventListener('submit', submitPdfForm);
    document.getElementById('page').addEventListener('change', toggleDriveFolderId);

    //promjena oznake unosa datoteke pri odabiru datoteke
    document.getElementById('pdfFile').addEventListener('change', function() {
        var fileName = this.files[0].name;
        var nextSibling = this.nextElementSibling;
        nextSibling.innerText = fileName;
    });
});
