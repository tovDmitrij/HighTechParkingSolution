from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from os.path import join, dirname
import psycopg2
app = Flask(__name__)
def get_from_env(key):
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    return os.environ.get(key)


@app.route("/", methods=["POST"])
def handle_telegram_message():

    data = request.json
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if text == "/start":

            try:
                cameras_response = requests.get("http://127.0.0.1:5000/api/v1/cameras")
                cameras_response.raise_for_status()

                cameras = cameras_response.json()
                if cameras:
                    text = "Здравствуйте, выберите камеру:"
                    keyboard = {
                        "inline_keyboard": [[{"text": camera["title"], "callback_data": f"camera_{camera['id']}"}] for
                                            camera in cameras]
                    }
                    send_message(chat_id, text, keyboard)
                    
                else:
                    send_message(chat_id, "Список камер пустой")
            except requests.exceptions.RequestException as e:
                print("Error fetching cameras:", e)
                send_message(chat_id, "Ошибка при получении списка камер")

    return "ok"
def send_message(chat_id, text, keyboard=None):
    token = get_from_env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(url, json=data)

@app.route('/api/v1/cameras', methods=['GET'])
def get_cameras():
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM cameras")
        cameras = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": row[0], "title": row[1]} for row in cameras]
    except psycopg2.Error as e:
        print("Error fetching cameras:", e)
        return None
def connect_to_db():
    conn = psycopg2.connect(
        dbname="parking",
        user="postgres",
        password="47template",
        host="localhost",
        port="5432"
    )
    return conn

if __name__ == '__main__':
    app.run()