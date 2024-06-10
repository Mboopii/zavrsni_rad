async function submitForm(event) {
    event.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const selectedPage = document.getElementById('page').value;
    const sheetUrl = document.getElementById('sheetUrl').value;
    const driveFolderIdHep = document.getElementById('driveFolderIdHep').value;
    const driveFolderIdVio = document.getElementById('driveFolderIdVio').value;
    const driveFolderIdA1 = document.getElementById('driveFolderIdA1').value;

    document.getElementById('loader').style.display = 'block';
    document.querySelector('.loader-background').style.display = 'block';

    try {
        const response = await fetch('https://web-scraping-8s0w.onrender.com/', {
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

        if (response.ok) {
            const data = await response.json();
            const requestId = data.request_id;
            document.getElementById('result').innerText = data.result;

            const statusInterval = setInterval(async () => {
                const statusResponse = await fetch(`https://web-scraping-8s0w.onrender.com/status/${requestId}`);
                if (statusResponse.ok) {
                    const statusData = await statusResponse.json();
                    if (statusData.success !== null) {
                        clearInterval(statusInterval);
                        document.getElementById('result').innerText = statusData.result;
                        document.getElementById('loader').style.display = 'none';
                        document.querySelector('.loader-background').style.display = 'none';
                    }
                }
            }, 2000);
        } else {
            document.getElementById('result').innerText = 'Greška pri prikupljanju podataka.';
            document.getElementById('loader').style.display = 'none';
            document.querySelector('.loader-background').style.display = 'none';
        }
    } catch (error) {
        console.error("Greška: ", error);
        document.getElementById('result').innerText = 'Došlo je do greške prilikom slanja zahtjeva.';
        document.getElementById('loader').style.display = 'none';
        document.querySelector('.loader-background').style.display = 'none';
    }
}

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
        const response = await fetch('https://web-scraping-8s0w.onrender.com/pdf/upload-invoice', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            const orderedKeys = [
                'invoice_number', 'customer_name', 'iban', 'invoice_date', 'due_date',
                'amount_due', 'total_amount', 'invoice_period', 'meter_readings'
            ];
            let resultHtml = '<table class="table table-bordered">';
            orderedKeys.forEach(key => {
                if (data[key] !== undefined) {
                    if (key === 'meter_readings') {
                        resultHtml += `<tr><td colspan="2"><strong>Meter Readings</strong></td></tr>`;
                        resultHtml += `<tr><td colspan="2"><table class="table table-bordered"><thead><tr><th>Date</th><th>Meter Number</th><th>Meter Reading</th><th>Consumption</th></tr></thead><tbody>`;
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
                        const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        resultHtml += `<tr><td><strong>${formattedKey}:</strong></td><td>${data[key]}</td></tr>`;
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

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginForm').addEventListener('submit', submitForm);
    document.getElementById('pdfForm').addEventListener('submit', submitPdfForm);
    document.getElementById('page').addEventListener('change', toggleDriveFolderId);
});
