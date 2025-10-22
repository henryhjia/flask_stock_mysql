import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

def date_format(x, pos=None):
    return mdates.num2date(x).strftime('%Y-%m-%d')

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/plot', methods=['POST'])
def plot():
    ticker = request.form['ticker'].upper()
    start_date = request.form['start_date']
    end_date = request.form['end_date']

    # Download the data
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True)
    
    new_columns = []
    for col in data.columns:
        if isinstance(col, tuple):
            new_columns.append(col[0].lower())
        else:
            new_columns.append(col.lower())
    data.columns = new_columns

    if data.empty:
        return render_template('error.html')

    data = data.sort_index(ascending=False)

    # Calculate statistics
    min_val = data['close'].min()
    min_price = min_val.iloc[0] if isinstance(min_val, pd.Series) else min_val
    max_val = data['close'].max()
    max_price = max_val.iloc[0] if isinstance(max_val, pd.Series) else max_val
    mean_val = data['close'].mean()
    mean_price = mean_val.iloc[0] if isinstance(mean_val, pd.Series) else mean_val

    # Generate the plot
    plot_data_df = data.sort_index(ascending=True)
    num_dates = len(plot_data_df.index)
    plt.figure(figsize=(10, 6))

    markersize = 5
    if num_dates > 50:
        markersize = 1
    elif num_dates > 20:
        markersize = 3

    plt.plot(range(num_dates), plot_data_df['close'], marker='o', markersize=markersize)
    plt.title(f'{ticker} Stock Price')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.grid(True)

    # Format the x-axis to show dates
    ax = plt.gca()
    if num_dates > 20:
        step = num_dates // 10
        ticks = range(0, num_dates, step)
        labels = [plot_data_df.index[i].strftime('%Y-%m-%d') for i in ticks]
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=90)
    else:
        ax.set_xticks(range(num_dates))
        ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in plot_data_df.index], rotation=90)
    plt.tight_layout() # Adjust layout to prevent labels from being cut off


    # Save it to a temporary buffer.
    buf = BytesIO()
    plt.savefig(buf, format="png")
    # Embed the result in the html output.
    plot_data = base64.b64encode(buf.getbuffer()).decode("ascii")
    plot_url = f'data:image/png;base64,{plot_data}'


    formatters = {
        'open': '{:.2f}'.format,
        'high': '{:.2f}'.format,
        'low': '{:.2f}'.format,
        'close': '{:.2f}'.format,
        'volume': '{:,}'.format
    }

    table_data = data
    if len(data) > 20:
        table_data = data.head(20)

    return render_template('result.html',
                           ticker=ticker,
                           min_price=f'{min_price:.2f}',
                           max_price=f'{max_price:.2f}',
                           mean_price=f'{mean_price:.2f}',
                           plot_url=plot_url,
                           data_table=table_data.to_html(classes=['table', 'table-striped'], header="true", formatters=formatters))

if __name__ == '__main__':
    app.run(debug=True)
