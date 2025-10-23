import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import os

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
import mysql.connector
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from werkzeug.security import generate_password_hash, check_password_hash

import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter


def date_format(x, pos=None):
    return mdates.num2date(x).strftime('%Y-%m-%d')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key'

# Database connection
def get_db_connection():
    connection = mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST"),
        user=os.environ.get("MYSQL_USER"),
        password=os.environ.get("MYSQL_PASSWORD"),
        database=os.environ.get("MYSQL_DB")
    )
    return connection
    return connection

# User model
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'], user_data['password'])
        return None

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('stock_viewer'))
    return redirect(url_for('login'))

@app.route('/stock_viewer')
@login_required
def stock_viewer():
    return render_template('stock_viewer.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('stock_viewer'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (form.username.data, form.email.data, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('stock_viewer'))
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (form.email.data,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        if user_data is None:
            flash('Account not found. Please register first.', 'info')
            return redirect(url_for('register'))
        if user_data and check_password_hash(user_data['password'], form.password.data):
            user = User(user_data['id'], user_data['username'], user_data['email'], user_data['password'])
            login_user(user)
            return redirect(url_for('stock_viewer'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/plot', methods=['POST'])
@login_required
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