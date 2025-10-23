import sys
import os



sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch
import pandas as pd
from app import app, get_db_connection, User
from werkzeug.security import generate_password_hash
from flask_login import login_user, current_user

class AppTestCase(unittest.TestCase):
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
                           ('testuser', 'test@example.com', hashed_password))
            conn.commit()
        except mysql.connector.Error as err:
            # If user already exists, ignore the error
            if "Duplicate entry" not in str(err):
                pass # Ignore duplicate entry error
            else:
                raise
        cursor.close()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        # Clean up the test user from the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", ('testuser',))
        conn.commit()
        cursor.close()
        conn.close()

    def setUp(self):
        # Manually log in the test user before each test
        with self.app as client:
            with client.session_transaction() as session:
                # Fetch the user from the database to get their ID
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id FROM users WHERE email = %s", ('test@example.com',))
                user_data = cursor.fetchone()
                cursor.close()
                conn.close()
                if user_data:
                    session['_user_id'] = str(user_data['id'])

    @patch('yfinance.download')
    def test_plot(self, mock_download):
        # Create a sample DataFrame to be returned by the mock
        data = {
            'open': [150, 151, 152],
            'high': [155, 156, 157],
            'low': [149, 150, 151],
            'close': [152, 153, 154],
            'volume': [1000, 1100, 1200]
        }
        dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        df = pd.DataFrame(data, index=dates)
        mock_download.return_value = df

        response = self.app.post('/plot', data={
            'ticker': 'AAPL',
            'start_date': '2023-01-01',
            'end_date': '2023-01-03'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AAPL Stock Price', response.data)
        self.assertIn(b'<strong>Min Price:</strong> 152.00', response.data)
        self.assertIn(b'<strong>Max Price:</strong> 154.00', response.data)
        self.assertIn(b'<strong>Mean Price:</strong> 153.00', response.data)
        self.assertIn(b'data:image/png;base64,', response.data)
        self.assertIn(b'<table border="1" class="dataframe table table-striped">', response.data)

    @patch('yfinance.download')
    def test_plot_long_range(self, mock_download):
        # Create a sample DataFrame with 30 days of data
        dates = pd.to_datetime(pd.date_range(start='2023-01-01', periods=30))
        data = {
            'open': [150 + i for i in range(30)],
            'high': [155 + i for i in range(30)],
            'low': [149 + i for i in range(30)],
            'close': [152 + i for i in range(30)],
            'volume': [1000 + i * 10 for i in range(30)]
        }
        df = pd.DataFrame(data, index=dates)
        mock_download.return_value = df

        response = self.app.post('/plot', data={
            'ticker': 'AAPL',
            'start_date': '2023-01-01',
            'end_date': '2023-01-30'
        })

        self.assertEqual(response.status_code, 200)
        # Check that the data is truncated to 20 days
        self.assertIn(b'2023-01-30', response.data)
        self.assertNotIn(b'2023-01-10', response.data)

    @patch('yfinance.download')
    def test_plot_no_data(self, mock_download):
        # Mock yfinance.download to return an empty DataFrame
        mock_download.return_value = pd.DataFrame()

        response = self.app.post('/plot', data={
            'ticker': 'INVALID',
            'start_date': '2023-01-01',
            'end_date': '2023-01-03'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>Error</title>', response.data)
        self.assertIn(b'No data found for the given ticker and date range.', response.data)
        self.assertIn(b'<a href="/stock_viewer" class="btn btn-primary btn-block">Go Back</a>', response.data)

if __name__ == '__main__':
    unittest.main()
