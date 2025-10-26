# Secure Stock Price Viewer 
## Project Overview

**Stock Price Viewer** is an enhanced version of the Stock Price Viewer application, designed to provide user authentication and secure data access.
The application is developed **with the help of AI-assisted programming using Gemini Pro 2.5,** improving development speed and reliability.

This app introduces a user registration and login system, ensuring that only registered users can access the stock data retrieval features.

Once logged in, users enter required fields:

- **Stock Ticker**
- **Start Date**
- **End Date**

The app will:

- Retrieve historical stock prices for the specified date range from Yahoo Finance.
- Generate a plot of stock price versus date for easy visualization.
- Display the most recent stock price, covering up to the last 20 days.

The application uses an **MySQL database** to manage user credentials and store application data.

## Features
🔐 **User Registration and Login** – Only registered users can access stock data.

📈 **Stock Data Retrieval** – Fetches historical data from Yahoo Finance.

📊 **Interactive Plot** – Displays stock price versus date.

💾 **SQLite Database** – Stores user information and application data locally.

⚡  **AI-Assisted Development** – Built efficiently with the help of Gemini.

## Running the Application Locally
  1. Activate the virtual environment 
  ```
  $ source venv/bin/activate
  ```
  2. Install the required dependencies
  ```
  $ pip install -r requirements.txt
  ```
  3. Start the Flask application
  ```
  $ python app.py
  ```
  4. Open the app in your browser to access [http://127.0.0.0:5000](http:/127/0/0/1:5000)
     **Secure Stock Data Viewer**

## Unit Test in local enrionment
```
  $ pytest
```
 
## Deployment to GCP
Once unit test passes, deploy it to GCP
```
  $ gcloud app deploy
```