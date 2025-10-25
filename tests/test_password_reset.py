
import sys
import os
import unittest
from unittest.mock import patch
from app import app, get_db_connection
from werkzeug.security import generate_password_hash
import secrets
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class PasswordResetTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app.test_client()
        cls.app.testing = True

        # Create a test user in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        hashed_password = generate_password_hash('testpassword', method='pbkdf2:sha256')
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                           ('testuser_reset', 'test_reset@example.com', hashed_password))
            conn.commit()
        except Exception as e:
            # If user already exists, ignore the error
            if "Duplicate entry" not in str(e):
                raise
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def tearDownClass(cls):
        # Clean up the test user from the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", ('testuser_reset',))
        conn.commit()
        cursor.close()
        conn.close()

    def test_forgot_password_page_loads(self):
        response = self.app.get('/forgot_password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reset Password', response.data)

    def test_forgot_password_with_valid_email(self):
        with self.app as client:
            response = client.get('/forgot_password')
            self.assertEqual(response.status_code, 200)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.data, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

            response = client.post('/forgot_password', data={'email': 'test_reset@example.com', 'csrf_token': csrf_token}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'A password reset link has been generated.', response.data)

    def test_forgot_password_with_invalid_email(self):
        with self.app as client:
            response = client.get('/forgot_password')
            self.assertEqual(response.status_code, 200)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.data, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

            response = client.post('/forgot_password', data={'email': 'nonexistent@example.com', 'csrf_token': csrf_token}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'There is no account with that email. You must register first.', response.data)

    def test_reset_password_with_valid_token(self):
        # Generate a token for the test user
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET reset_token = %s, reset_token_expiration = %s WHERE email = %s",
                       (token, expires_at, 'test_reset@example.com'))
        conn.commit()
        cursor.close()
        conn.close()

        response = self.app.get(f'/reset_password/{token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reset Password', response.data)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

        # Test password reset submission
        response = self.app.post(f'/reset_password/{token}', data={
            'password': 'newpassword',
            'confirm_password': 'newpassword',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your password has been updated!', response.data)

    def test_reset_password_with_invalid_token(self):
        response = self.app.get('/reset_password/invalidtoken', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'That is an invalid or expired token', response.data)

    def test_reset_password_with_expired_token(self):
        # Generate an expired token for the test user
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() - timedelta(hours=1)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET reset_token = %s, reset_token_expiration = %s WHERE email = %s",
                       (token, expires_at, 'test_reset@example.com'))
        conn.commit()
        cursor.close()
        conn.close()

        response = self.app.get(f'/reset_password/{token}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'That is an invalid or expired token', response.data)

if __name__ == '__main__':
    unittest.main()
