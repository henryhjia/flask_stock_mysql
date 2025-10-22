import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch
import pandas as pd
from app import app

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

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
        self.assertIn(b'<a href="/" class="btn btn-primary btn-block">Go Back</a>', response.data)

if __name__ == '__main__':
    unittest.main()
