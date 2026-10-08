import io
import json
import unittest
from app import app
import database

class DocSnapPlatformTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        database.init_db()

    def test_01_index_and_routes(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'DocSnap', res.data)
        self.assertIn(b'History', res.data)
        self.assertIn(b'Dashboard', res.data)
        self.assertIn(b'Verification Agent', res.data)

    def test_02_sample_timetable_extraction(self):
        with open('static/samples/sample_timetable.png', 'rb') as f:
            img_bytes = f.read()
        res = self.client.post('/extract', data={
            'image': (io.BytesIO(img_bytes), 'sample_timetable.png')
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertEqual(data['doc_type'], 'timetable')
        self.assertIn('verification_report', data)
        self.assertIn('id', data)
        self.assertIn('versions', data)
        self.assertEqual(len(data['versions']), 1)
        self.assertEqual(data['versions'][0]['version_label'], '🤖 AI Generated')

    def test_03_sample_receipt_extraction_and_math_audit(self):
        with open('static/samples/sample_receipt.png', 'rb') as f:
            img_bytes = f.read()
        res = self.client.post('/extract', data={
            'image': (io.BytesIO(img_bytes), 'sample_receipt.png')
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertEqual(data['doc_type'], 'receipt')
        self.assertIn('verification_report', data)
        self.assertIn('passed_checks', data['verification_report'])
        self.assertTrue(len(data['verification_report']['passed_checks']) > 0)

    def test_04_sample_notice_extraction(self):
        with open('static/samples/sample_notice.png', 'rb') as f:
            img_bytes = f.read()
        res = self.client.post('/extract', data={
            'image': (io.BytesIO(img_bytes), 'sample_notice.png')
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertEqual(data['doc_type'], 'notice')

    def test_05_human_verification_and_version_history(self):
        # 1. Create a document
        doc = database.create_document(
            filename='test_notice.png',
            doc_type='notice',
            ai_extracted_data={'title': 'AI Hackathon', 'venue': 'Room 101', 'date': '2026-10-15'}
        )
        doc_id = doc['id']
        self.assertEqual(len(doc['versions']), 1)
        self.assertEqual(doc['versions'][0]['version_label'], '🤖 AI Generated')

        # 2. User edits field (Version 2)
        edited_data = {'title': 'AI Hackathon 2026', 'venue': 'Auditorium Hall B', 'date': '2026-10-15'}
        res = self.client.put(f'/api/documents/{doc_id}', json={'data': edited_data})
        self.assertEqual(res.status_code, 200)
        updated = res.json
        self.assertEqual(len(updated['versions']), 2)
        self.assertEqual(updated['versions'][1]['version_label'], '👤 User Edited')

        # 3. Human Verifier clicks Verify & Save (Version 3)
        res_verify = self.client.post(f'/api/documents/{doc_id}/verify', json={'data': edited_data})
        self.assertEqual(res_verify.status_code, 200)
        verified = res_verify.json
        self.assertEqual(verified['verification_status'], 'verified')
        self.assertEqual(len(verified['versions']), 3)
        self.assertEqual(verified['versions'][2]['version_label'], '✅ Verified')

        # 4. Check Diff comparison between AI and Verified data
        res_ver_diff = self.client.get(f'/api/documents/{doc_id}/versions')
        self.assertEqual(res_ver_diff.status_code, 200)
        diff_payload = res_ver_diff.json
        self.assertEqual(diff_payload['ai_extracted_data']['venue'], 'Room 101')
        self.assertEqual(diff_payload['verified_data']['venue'], 'Auditorium Hall B')

    def test_06_ask_your_document_ai(self):
        # 1. Receipt test
        res = self.client.post('/api/document/ask', json={
            'doc_type': 'receipt',
            'data': {'merchant': 'City Bakery', 'total': 350.0, 'items': [{'name': 'Croissant', 'qty': 2, 'price': 175.0}]},
            'question': 'What is the total amount?'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('350', res.json['answer'])

        # 2. Timetable test with acronyms (DSA -> Data Structures)
        tt_res = self.client.post('/api/document/ask', json={
            'doc_type': 'timetable',
            'data': {
                'title': 'Semester 4 Schedule',
                'entries': [
                    {'subject': 'Data Structures & Algorithms', 'day': 'Monday', 'start_time': '09:00', 'end_time': '10:30', 'room': 'Room 302', 'faculty': 'Prof. Sharma'},
                    {'subject': 'Computer Networks', 'day': 'Tuesday', 'start_time': '11:00', 'end_time': '12:30', 'room': 'Room 204', 'faculty': 'Dr. Patel'}
                ]
            },
            'question': 'Where is the DSA lecture?'
        })
        self.assertEqual(tt_res.status_code, 200)
        self.assertIn('302', tt_res.json['answer'])

    def test_07_smart_summary(self):
        res = self.client.post('/api/document/summary', json={
            'doc_type': 'timetable',
            'data': {
                'title': 'Semester 4 Schedule',
                'entries': [{'subject': 'DSA', 'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00', 'room': 'Lab 1', 'faculty': 'Prof A'}]
            }
        })
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn('important_points', data)
        self.assertTrue(len(data['important_points']) > 0)

    def test_08_translation(self):
        res = self.client.post('/api/translate', json={
            'data': {'title': 'Pariksha Time Table', 'subject': 'Ganit'},
            'target_language': 'English'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('original', res.json)
        self.assertIn('translated', res.json)

    def test_09_export_endpoints(self):
        # 1. ICS Calendar export
        res_ics = self.client.post('/export/ics', json={
            'doc_type': 'timetable',
            'data': {
                'title': 'Weekly Classes',
                'entries': [{'subject': 'DSA', 'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00', 'room': '302', 'faculty': 'Dr Patel'}]
            }
        })
        self.assertEqual(res_ics.status_code, 200)
        self.assertIn(b'BEGIN:VCALENDAR', res_ics.data)

        # 2. CSV export
        res_csv = self.client.post('/export/csv', json={
            'doc_type': 'receipt',
            'data': {
                'merchant': 'Cafe',
                'date': '2026-10-01',
                'total': 150,
                'items': [{'name': 'Coffee', 'qty': 1, 'price': 150}]
            }
        })
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn(b'Merchant,Date,Category', res_csv.data)

        # 3. Excel export
        res_excel = self.client.post('/export/excel', json={
            'doc_type': 'receipt',
            'data': {
                'merchant': 'Cafe',
                'date': '2026-10-01',
                'total': 150,
                'items': [{'name': 'Coffee', 'qty': 1, 'price': 150}]
            }
        })
        self.assertEqual(res_excel.status_code, 200)
        self.assertTrue(len(res_excel.data) > 1000)

    def test_10_analytics_and_history(self):
        res_analytics = self.client.get('/api/analytics')
        self.assertEqual(res_analytics.status_code, 200)
        self.assertIn('total_documents', res_analytics.json)
        self.assertIn('verified_count', res_analytics.json)

        res_history = self.client.get('/api/documents')
        self.assertEqual(res_history.status_code, 200)
        self.assertIn('documents', res_history.json)

    def test_11_invalid_upload_handling(self):
        # Empty payload
        res = self.client.post('/extract', data={})
        self.assertEqual(res.status_code, 400)

        # Corrupted bytes file
        res2 = self.client.post('/extract', data={
            'image': (io.BytesIO(b'not-an-image'), 'corrupt.png')
        }, content_type='multipart/form-data')
        self.assertEqual(res2.status_code, 400)

if __name__ == '__main__':
    unittest.main()
