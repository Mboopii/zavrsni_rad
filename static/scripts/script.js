async function submitForm(event) {
    event.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const selectedPage = document.getElementById('page').value;

    document.getElementById('loader').style.display = 'block';
    document.querySelector('.loader-background').style.display = 'block';

    try {
        const response = await fetch('https://rad-hom7.onrender.com/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password, selectedPage }),
        });

        if (response.ok) {
            const data = await response.json();
            const requestId = data.request_id;
            document.getElementById('result').innerText = data.result;

            const statusInterval = setInterval(async () => {
                const statusResponse = await fetch(`https://rad-hom7.onrender.com/status/${requestId}`);
                if (statusResponse.ok) {
                    const statusData = await statusResponse.json();
                    if (statusData.success !== null) {
                        clearInterval(statusInterval);
                        document.getElementById('result').innerText = statusData.result;
                        document.getElementById('loader').style.display = 'none';
                        document.querySelector('.loader-background').style.display = 'none';
                    }
                }
            }, 2000); // Check status every 2 seconds
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

async function checkStatus(requestId) {
    let status = 'processing';
    while (status === 'processing') {
        const response = await fetch(`https://rad-hom7.onrender.com/status/${requestId}`);
        const data = await response.json();
        status = data.status;

        if (status === 'completed') {
            document.getElementById('result').innerText = 'Podatci uspješno upisani u Google Sheets.';
        } else if (status === 'error') {
            document.getElementById('result').innerText = 'Greška pri prikupljanju podataka.';
        }

        await new Promise(resolve => setTimeout(resolve, 1000)); // wait for 1 second before next poll
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginForm').addEventListener('submit', submitForm);
});

async function submitMeterForm(event) {
    event.preventDefault();

    const form = document.getElementById('meterForm');
    const formData = new FormData(form);

    document.getElementById('loader').style.display = 'block';
    document.querySelector('.loader-background').style.display = 'block';

    try {
        const response = await fetch('https://rad-hom7.onrender.com/submit-meter-reading', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('meter-result').innerText = data.message;
        } else {
            document.getElementById('meter-result').innerText = 'Greška pri slanju očitanja brojila.';
        }
    } catch (error) {
        console.error("Greška: ", error);
        document.getElementById('meter-result').innerText = 'Greška pri slanju očitanja brojila.';
    } finally {
        document.getElementById('loader').style.display = 'none';
        document.querySelector('.loader-background').style.display = 'none';
    }
}

async function submitPdfForm(event) {
    event.preventDefault();

    const form = document.getElementById('pdfForm');
    const formData = new FormData(form);

    const invoiceType = document.getElementById('invoiceType').value;
    formData.append('invoice_type', invoiceType);

    document.getElementById('loader').style.display = 'block';
    document.querySelector('.loader-background').style.display = 'block';

    try {
        const response = await fetch('https://rad-hom7.onrender.com/pdf/upload-invoice', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            const orderedKeys = [
                'invoice_number', 'customer_name', 'invoice_date', 'due_date',
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
    document.getElementById('meterForm').addEventListener('submit', submitMeterForm);
    document.getElementById('pdfForm').addEventListener('submit', submitPdfForm);
});
