import json

from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import cv2
import os
from os.path import join, dirname
import psycopg2
import numpy as np
from PIL import Image
import io
from yolo.main import predictions


app = Flask(__name__)
def get_from_env(key):
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    return os.environ.get(key)


@app.route("/", methods=["POST"])
def handle_telegram_message():
    print(request.json)
    data = request.json
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if text == "/start":
            message_id = send_waiting_message(chat_id)
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
                    if message_id:
                        delete_waiting_message(chat_id, message_id)
                else:
                    send_message(chat_id, "Список камер пустой")
            except requests.exceptions.RequestException as e:
                print("Error fetching cameras:", e)
                send_message(chat_id, "Ошибка при получении списка камер")
    if "callback_query" in data:
        handle_callback_query(data)

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
@app.route('/api/v1/cameras/<int:camera_id>', methods=['GET'])
def get_camera_url(camera_id):
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT url FROM cameras WHERE id=%s", (camera_id,))
        url = cur.fetchone()[0]
        cur.close()
        conn.close()
        return url
    except psycopg2.Error as e:
        print("Error fetching url camera:", e)
        return None


def get_camera_frameCV(url):
    try:
        # Загрузка кадра с камеры по URL
        response = requests.get(url)
        response.raise_for_status()

        # Преобразование полученных данных в изображение
        image = Image.open(io.BytesIO(response.content))

        # Преобразование изображения в массив numpy
        image_array = np.array(image)
        return image_array
    except Exception as e:
        print("Error fetching camera frame:", e)
        return None

def get_camera_frame(url):
    try:
        # Загрузка кадра с камеры по URL
        response = requests.get(url)
        response.raise_for_status()

        # Преобразование полученных данных в изображение
        image = Image.open(io.BytesIO(response.content))

        # Преобразование изображения в формат JPEG
        with io.BytesIO() as output:
            image.save(output, format="JPEG")
            frame = output.getvalue()

        return frame
    except Exception as e:
        print("Error fetching camera frame:", e)
        return None

def handle_callback_query(data):
    if "callback_query" in data:
        callback_query = data["callback_query"]
        chat_id = callback_query["message"]["chat"]["id"]
        callback_data = callback_query["data"]
        message_id = send_waiting_message(chat_id)

    # Обработка нажатия на кнопку "camera_<camera_id>"
        if callback_data.startswith("camera_"):
            camera_id = int(callback_data.split("_")[1])
            try:
                urlFrame_response = requests.get(f"http://127.0.0.1:5000/api/v1/cameras/{camera_id}")

                urlFrame_response.raise_for_status()

                frame = get_camera_frame(urlFrame_response.text)

                if frame:
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "Показать свободные парковочные места", "callback_data": f"showFreeSpaces_{camera_id}"}]
                        ]
                    }
                    #send_photo(chat_id, frame)
                    send_message_with_photo_and_keyboard(chat_id, frame, keyboard)
                    if message_id:
                        delete_waiting_message(chat_id, message_id)
                    return
            except requests.exceptions.RequestException as e:
                print("Error frame receiving:", e)
                send_message(chat_id, "Ошибка при получении кадра")
                return
        # Обработка нажатия на кнопку "Показать свободные парковочные места"
        if callback_data.startswith("showFreeSpaces_"):
            camera_id = int(callback_data.split("_")[1])
            try:
                urlFrame_response = requests.get(f"http://127.0.0.1:5000/api/v1/cameras/{camera_id}")

                urlFrame_response.raise_for_status()

                frame = get_camera_frameCV(urlFrame_response.text)
                arr, freeImg = predictions(frame)

                caption = ", ".join(arr)
                send_photo_with_caption(chat_id, freeImg, caption)
                if message_id:
                    delete_waiting_message(chat_id, message_id)
                return

            except requests.exceptions.RequestException as e:
                print("Error frame receiving:", e)
                send_message(chat_id, "Ошибка при получении размеченного кадра с подписью")
                return


def send_photo(chat_id, photo):
    token = get_from_env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    files = {"photo": photo}
    data = {"chat_id": chat_id}
    requests.post(url, files=files, data=data)

def send_message_with_photo_and_keyboard(chat_id, photo, keyboard):
    token = get_from_env("TELEGRAM_BOT_TOKEN")
    url_send_photo = f"https://api.telegram.org/bot{token}/sendPhoto"

    files = {"photo": photo}
    data = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(keyboard)
    }

    try:
        requests.post(url_send_photo, files=files, data=data)

    except requests.exceptions.RequestException as e:
        print("Error sending message with photo and keyboard:", e)

def send_photo_with_caption(chat_id, image_array, caption):
    try:
        # Преобразование массива numpy обратно в изображение
        image = Image.fromarray(image_array.astype('uint8'))

        # Преобразование изображения в формат JPEG
        with io.BytesIO() as output:
            image.save(output, format="JPEG")
            photo = output.getvalue()

        # Отправка фото с подписью
        token = get_from_env("TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        files = {"photo": photo}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()

    except Exception as e:
        print("Error sending photo with caption:", e)
def send_waiting_message(chat_id):
    token = get_from_env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": "Ожидайте загрузки..."}
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["result"]["message_id"]
def delete_waiting_message(chat_id, message_id):
    try:
        token = get_from_env("TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{token}/deleteMessage"
        data = {"chat_id": chat_id, "message_id": message_id}
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print("Error deleting waiting message:", e)
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