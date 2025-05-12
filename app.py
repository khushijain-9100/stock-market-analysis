from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from forms import RegistrationForm, LoginForm

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User model for authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    return render_template("home.html")

# Function to fetch real-time stock, crypto, and gold prices
def get_live_data():
    stock_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    crypto_symbols = ["BTC-USD", "ETH-USD"]
    gold_symbol = "GC=F"
    live_data = []

    for symbol in stock_symbols + crypto_symbols + [gold_symbol]:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if not data.empty:
            price = round(data['Close'].iloc[-1], 2)
            change = round(price - data['Open'].iloc[-1], 2)
            percent_change = f"{'+' if change >= 0 else ''}{round((change / data['Open'].iloc[-1]) * 100, 2)}%"
            live_data.append({
                "symbol": symbol.replace("-USD", ""),
                "price": price,
                "change": percent_change,
                "status": "Open" if "USD" not in symbol else "24/7"
            })
    return live_data

# Function to generate multiple stock analysis graphs
def generate_stock_graphs(stock_symbol):
    timeframes = {"5m": "5m", "1d": "1d", "5d": "5d", "1mo": "1mo", "1y": "1y", "2y": "2y"}
    graph_paths = {}

    for label, period in timeframes.items():
        stock = yf.Ticker(stock_symbol)
        df = stock.history(period=period, interval="1d" if period in ["1mo", "1y", "2y"] else "5m")

        if df.empty:
            continue

        df['20-day MA'] = df['Close'].rolling(window=20).mean()
        df['50-day MA'] = df['Close'].rolling(window=50).mean()
        df['200-day MA'] = df['Close'].rolling(window=200).mean()

        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df['Close'], label="Closing Price", color="blue")
        plt.plot(df.index, df['20-day MA'], label="20-day MA", color="green")
        plt.plot(df.index, df['50-day MA'], label="50-day MA", color="orange")
        plt.plot(df.index, df['200-day MA'], label="200-day MA", color="red")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.title(f"{stock_symbol} Price Trend ({label})")
        plt.legend()
        plt.grid()

        graph_filename = f"static/{stock_symbol}_{label}_graph.png"
        plt.savefig(graph_filename)
        plt.close()
        graph_paths[label] = graph_filename

    return graph_paths

@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    stock_data = None
    graph_paths = None
    live_data = get_live_data()

    if request.method == "POST":
        stock_symbol = request.form.get("symbol")
        if stock_symbol:
            stock_symbol = stock_symbol.upper()
            try:
                stock = yf.Ticker(stock_symbol)
                df = stock.history(period="6mo")

                if df.empty:
                    flash(f"No data found for stock symbol: {stock_symbol}", "warning")
                else:
                    current_price = df['Close'].iloc[-1]
                    day_high = df['High'].iloc[-1]
                    day_low = df['Low'].iloc[-1]

                    graph_paths = generate_stock_graphs(stock_symbol)

                    stock_data = {
                        "symbol": stock_symbol,
                        "current_price": round(current_price, 2),
                        "day_high": round(day_high, 2),
                        "day_low": round(day_low, 2)
                    }
            except Exception as e:
                flash(f"Error fetching data for {stock_symbol}: {e}", "danger")

    return render_template("index.html", stock_data=stock_data, graph_paths=graph_paths, live_data=live_data)

@app.route("/api/live-data")
def live_data_api():
    return jsonify(get_live_data())

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully!", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    with app.app_context():
        db.create_all()
    app.run(debug=True)
