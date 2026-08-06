import unittest
import json
from app import app

class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, {"status": "ok"})

    def test_hello_missing_name(self):
        response = self.client.get('/hello')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Missing required query parameter: name")

    def test_hello_empty_name(self):
        response = self.client.get('/hello?name=')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data["error"], "Missing required query parameter: name")

    def test_hello_whitespace_name(self):
        response = self.client.get('/hello?name=%20%20')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data["error"], "Missing required query parameter: name")

    def test_hello_success(self):
        response = self.client.get('/hello?name=Alice')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, {"message": "Hello, Alice!"})

    def test_goodbye_missing_name(self):
        response = self.client.get('/goodbye')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data["error"], "Missing required query parameter: name")

    def test_goodbye_success(self):
        response = self.client.get('/goodbye?name=Bob')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, {"message": "Goodbye, Bob!"})

if __name__ == '__main__':
    unittest.main()
