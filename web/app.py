# web/app.py

import os
import sys
import sqlite3
from multiprocessing import Process, Value
import time

# Імпортуємо нові бібліотеки
import psutil

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash

# Додаємо шлях до кореневої директорії для імпортів
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Конфігурація для управління процесом ---
PID_FILE = "bot.pid"  # Назва файлу для зберігання ID процесу


def run_bot():
    """Функція для запуску бота в окремому процесі."""
    from main import main
    import asyncio
    print("Bot process started...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot process received KeyboardInterrupt.")
    finally:
        print("Bot process stopped.")


# --- Функції для управління PID файлом ---

def process_is_running():
    """Перевіряє, чи запущений процес, на основі PID файлу."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # psutil.pid_exists - найнадійніший спосіб перевірки
        return psutil.pid_exists(pid)
    except (IOError, ValueError, psutil.NoSuchProcess):
        # Якщо файл пошкоджений або процес вже не існує
        cleanup_pid_file()
        return False


def cleanup_pid_file():
    """Видаляє PID файл, якщо він існує."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


# --- Ініціалізація Flask ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)


# --- Маршрути Flask ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        admin_id = request.form.get('id')
        password = request.form.get('password')
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("SELECT password, username FROM admins WHERE id = ?", (admin_id,))
        admin_data = cur.fetchone()
        con.close()
        if admin_data and check_password_hash(admin_data[0], password):
            session.clear()
            session['admin_id'] = admin_id
            session['username'] = admin_data[1]
            return redirect(url_for('dashboard'))
        else:
            error = "Неправильний ID або пароль."
    return render_template('login.html', error=error)


@app.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session.get('username'))


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/start-bot', methods=['POST'])
def start_bot_route():
    if process_is_running():
        return jsonify({"status": "Bot is already running."})

    # Створюємо та запускаємо новий процес
    bot_process = Process(target=run_bot)
    bot_process.start()

    # Записуємо PID нового процесу у файл
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(bot_process.pid))
        return jsonify({"status": "Bot starting..."})
    except IOError as e:
        return jsonify({"status": f"Error writing PID file: {e}"}), 500


@app.route('/stop-bot', methods=['POST'])
def stop_bot_route():
    if not os.path.exists(PID_FILE):
        return jsonify({"status": "Bot is not running (PID file not found)."})
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())

        process = psutil.Process(pid)
        process.terminate()  # Жорстке, але надійне завершення
        process.wait(timeout=3)  # Чекаємо до 3 секунд, поки процес завершиться

        cleanup_pid_file()
        return jsonify({"status": "Bot stopped."})
    except (IOError, ValueError):
        cleanup_pid_file()
        return jsonify({"status": "Stale PID file found and removed. Bot was not running."})
    except psutil.NoSuchProcess:
        cleanup_pid_file()
        return jsonify({"status": "Bot was not running (process not found)."})
    except psutil.TimeoutExpired:
        return jsonify({"status": "Failed to stop the bot within 3 seconds."}), 500


@app.route('/bot-status')
def bot_status_route():
    """Єдиний надійний спосіб перевірки статусу."""
    if process_is_running():
        return jsonify({"status": "running"})
    else:
        return jsonify({"status": "stopped"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)