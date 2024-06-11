import unittest
from unittest.mock import MagicMock, Mock, patch

import requests
import requests_mock
from app import create_worksheets, prijava, process_request
from gpz import dohvati_podatke_gpz
from vio import dohvati_podatke_vio
from hep import dohvati_podatke_hep
from a1 import dohvati_podatke_a1
from upload import upload_pdf_to_drive
from pdf import extract_text_from_pdf
import io
from datetime import datetime

class TestGoogleSheets(unittest.TestCase):

    @patch('gspread.Spreadsheet')
    def test_create_worksheets(self, MockSpreadsheet):
        mock_worksheet_hep = Mock()
        mock_worksheet_hep.title = 'hep'
        
        mock_worksheet_gpz = Mock()
        mock_worksheet_gpz.title = 'gpz'
        
        mock_sheet = MockSpreadsheet()
        mock_sheet.worksheets.return_value = [mock_worksheet_hep, mock_worksheet_gpz]
        
        create_worksheets(mock_sheet)
        
        self.assertEqual(mock_sheet.add_worksheet.call_count, 2)


class TestPrijava(unittest.TestCase):

    @patch('requests.Session.post')
    def test_prijava_hep_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Token': 'fake_token',
            'Korisnik': {'Kupci': [{'KupacId': '123456'}]}
        }
        mock_post.return_value = mock_response

        session, kupac_id = prijava('test@example.com', 'password', 'hep')
        self.assertIsNotNone(session)
        self.assertIsNotNone(kupac_id)
        self.assertEqual(kupac_id, '123456')

    @patch('requests.Session.post')
    def test_prijava_hep_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        session = prijava('test@example.com', 'wrong_password', 'hep')
        self.assertIsNone(session)

    @patch('requests.Session.post')
    def test_prijava_vio_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        session = prijava('test@example.com', 'password', 'vio')
        self.assertIsNotNone(session)

    @patch('requests.Session.post')
    def test_prijava_vio_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        session = prijava('test@example.com', 'wrong_password', 'vio')
        self.assertIsNone(session)

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_prijava_gpz_success(self, mock_get, mock_post):
        mock_response_post = Mock()
        mock_response_post.status_code = 302
        mock_response_post.headers = {'Location': 'https://mojracun.gpz-opskrba.hr/some_redirect'}
        mock_post.return_value = mock_response_post
        
        mock_response_get = Mock()
        mock_response_get.status_code = 200
        mock_get.return_value = mock_response_get
        
        session = prijava('test@example.com', 'password', 'gpz')
        self.assertIsNotNone(session)

    @patch('requests.Session.post')
    def test_prijava_gpz_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        session = prijava('test@example.com', 'wrong_password', 'gpz')
        self.assertIsNone(session)

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_prijava_a1_success(self, mock_get, mock_post):
        mock_response_post = Mock()
        mock_response_post.status_code = 302
        mock_response_post.headers = {'Location': 'https://moj.a1.hr/postpaid/residential/potrosnja'}
        mock_post.return_value = mock_response_post
        
        mock_response_get1 = Mock()
        mock_response_get1.status_code = 302
        mock_response_get1.headers = {'Location': 'https://moj.a1.hr/some_redirect'}
        
        mock_response_get2 = Mock()
        mock_response_get2.status_code = 200
        
        mock_get.side_effect = [mock_response_get1, mock_response_get2]
        
        session = prijava('test@example.com', 'password', 'a1')
        self.assertIsNotNone(session)

    @patch('requests.Session.post')
    def test_prijava_a1_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        session = prijava('test@example.com', 'wrong_password', 'a1')
        self.assertIsNone(session)

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_prijava_a1_redirect_failure(self, mock_get, mock_post):
        mock_response_post = Mock()
        mock_response_post.status_code = 302
        mock_response_post.headers = {'Location': 'https://moj.a1.hr/postpaid/residential/potrosnja'}
        mock_post.return_value = mock_response_post
        
        mock_response_get1 = Mock()
        mock_response_get1.status_code = 302
        mock_response_get1.headers = {'Location': 'https://moj.a1.hr/some_redirect'}
        
        mock_response_get2 = Mock()
        mock_response_get2.status_code = 401
        
        mock_get.side_effect = [mock_response_get1, mock_response_get2]
        
        session = prijava('test@example.com', 'password', 'a1')
        self.assertIsNone(session)

class TestGPZ(unittest.TestCase):
    @patch('requests.Session')
    def test_dohvati_podatke_gpz_new_data(self, MockSession):
        mock_session = MockSession.return_value
        mock_response = MagicMock()
        mock_response.content = '<tr><td>15.01.2022</td><td>FAKTURA</td><td>100</td><td></td></tr>'
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = [['Datum', 'Vrsta', 'Iznos računa', 'Iznos uplate']]
        mock_worksheet.cell.return_value.value = ''

        result, success = dohvati_podatke_gpz(mock_session, mock_worksheet)

        self.assertTrue(success)
        self.assertEqual(result, 'Podaci uspješno uneseni u radni list')
        mock_worksheet.insert_rows.assert_called_once()
        mock_worksheet.append_row.assert_not_called()

    @patch('requests.Session')
    def test_dohvati_podatke_gpz_no_new_data(self, MockSession):
        mock_session = MockSession.return_value
        mock_response = MagicMock()
        mock_response.content = '<tr><td>14.01.2022</td><td>FAKTURA</td><td>100</td><td></td></tr>'
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = [['Datum', 'Vrsta', 'Iznos računa', 'Iznos uplate']]
        mock_worksheet.cell.return_value.value = '15.01.2022'

        result, success = dohvati_podatke_gpz(mock_session, mock_worksheet)

        self.assertTrue(success)
        self.assertEqual(result, 'Nema novih računa.')
        mock_worksheet.insert_rows.assert_not_called()
        mock_worksheet.append_row.assert_not_called()

class TestVIO(unittest.TestCase):
    @requests_mock.Mocker()
    @patch('vio.upload_pdf_to_drive', return_value='fake_link')
    def test_dohvati_podatke_vio(self, mock_requests, mock_upload):
        mock_html_content = '''
        <table>
            <tr>
                <td>01.06.2024</td>
                <td>10.06.2024</td>
                <td>Racun</td>
                <td>100.00</td>
                <td>0.00</td>
                <td style="text-align:center;cursor:pointer;"><a href="/download/pdf/12345">PDF</a></td>
            </tr>
        </table>
        '''
        mock_requests.get('https://www.vio.hr/mojvio/?v=uplate', text=mock_html_content)

        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = []
        mock_worksheet.cell.return_value.value = '01.05.2024'

        result, success = dohvati_podatke_vio(requests.Session(), mock_worksheet, 'fake_parent_folder_id')
        
        self.assertTrue(success)
        self.assertEqual(mock_upload.call_count, 1)
        mock_worksheet.append_row.assert_called_with(['Datum', 'Datum dospijeća', 'Vrsta', 'Iznos računa', 'Iznos uplate', 'Link na PDF'])
        mock_worksheet.insert_rows.assert_called()

class TestHEP(unittest.TestCase):

    @patch('hep.upload_pdf_to_drive')
    def test_dohvati_podatke_hep(self, mock_upload_pdf_to_drive):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'promet_lista': [
                {
                    'Datum': '2024-06-11T00:00:00',
                    'Opis': 'Račun',
                    'Duguje': 100,
                    'Potrazuje': 0,
                    'Racun': '12345'
                }
            ]
        }
        mock_session.get.return_value = mock_response

        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = []  
        mock_worksheet.cell.return_value.value = None

        mock_upload_pdf_to_drive.return_value = 'https://drive.google.com/file/d/12345/view'

        kupac_id = 'test_kupac_id'
        parent_folder_id = 'test_folder_id'

        result, success = dohvati_podatke_hep(mock_session, mock_worksheet, kupac_id, parent_folder_id)

        self.assertTrue(success)
        self.assertIn('Podaci uspješno uneseni u radni list', result)


class TestA1(unittest.TestCase):
    @requests_mock.Mocker()
    @patch('a1.upload_pdf_to_drive', return_value='fake_link')
    def test_dohvati_podatke_a1(self, mock_requests, mock_upload):
        mock_html_content = '''
        <div class="mv-Payment g-12 g-reset g-rwd p">
            <div class="mv-Payment-period mv-Payment-infoCell mv-Payment-infoCell g-4">
                <div class="u-fontStrong u-textCenter">05/2024</div>
            </div>
            <div class="mv-Payment-sum mv-Payment-infoCell mv-Payment-infoCell g-4">
                <div class="u-fontStrong u-textCenter">100.00</div>
            </div>
            <div class="mv-Payment-due mv-Payment-infoCell mv-Payment-infoCell g-4">
                <div class="u-fontStrong u-textCenter">10.06.2024</div>
            </div>
            <a class="bill_pdf_export" href="/download/pdf/12345"></a>
        </div>
        '''
        mock_requests.get('https://moj.a1.hr/postpaid/residential/pregled-racuna', text=mock_html_content)

        mock_worksheet = MagicMock()
        mock_worksheet.get_all_values.return_value = []
        mock_worksheet.cell.return_value.value = '04/2024'
        
        result, success = dohvati_podatke_a1(requests.Session(), mock_worksheet, 'fake_parent_folder_id')
        
        self.assertTrue(success)
        self.assertEqual(mock_upload.call_count, 1)
        mock_worksheet.append_row.assert_called_with(['Datum', 'Vrsta', 'Iznos računa', 'Datum dospijeća', 'Link na PDF'])
        mock_worksheet.insert_rows.assert_called()

class TestUploadPDF(unittest.TestCase):
    @patch('upload.build')
    @patch('requests.Session')
    def test_upload_pdf_to_drive(self, MockSession, mock_build):
        mock_session = MockSession.return_value

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.content = b'PDF content'
        mock_session.get.return_value = mock_get_response
        
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.content = b'PDF content'
        mock_session.post.return_value = mock_post_response

        mock_drive_service = MagicMock()
        mock_files = MagicMock()
        mock_files.create.return_value.execute.return_value = {'webViewLink': 'fake_link'}
        mock_drive_service.files.return_value = mock_files
        mock_build.return_value = mock_drive_service

        result = upload_pdf_to_drive(mock_session, 'https://test.com/pdf', '01.01.2024', 'parent_folder_id')
        self.assertIn('fake_link', result)

        result_with_payload = upload_pdf_to_drive(mock_session, 'https://test.com/pdf', '01.01.2024', 'parent_folder_id', payload={'key': 'value'})
        self.assertIn('fake_link', result_with_payload)
        
class TestPDFExtraction(unittest.TestCase):

    @patch('pdf.fitz.open')
    def test_extract_text_from_pdf(self, mock_fitz_open):
        mock_pdf_document = Mock()
        mock_fitz_open.return_value = mock_pdf_document
        
        mock_page = Mock()
        mock_page.get_text.return_value = 'Test Content '
        mock_pdf_document.page_count = 2
        mock_pdf_document.load_page.return_value = mock_page
        
        content = extract_text_from_pdf('test.pdf')
        self.assertEqual(content, 'Test Content Test Content ')

if __name__ == '__main__':
    unittest.main()
