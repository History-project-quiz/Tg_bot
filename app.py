import os
import random

import telebot
from dotenv import load_dotenv
import requests
from telebot import types

load_dotenv()
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN"))
PASSWORD = os.environ.get("PASSWORD")
API_PREFIX = os.environ.get("API_PREFIX")
QUESTIONS = [
    {"question": "Назовите фильм, массовая сцена из которого занесена в книгу рекордов Гинесса",
     "image": None,
     "ans": "«война и мир»",
     "variants": ["«Белое солнце пустыни»", "«Солярис»", "«Война и мир»",
                  "Киноэпопея «Освобождение»"],
     "score": 1},
    {"question": "Кто изображен на фотографии?",
     "image": r"static/bondarchuk.jpg",
     "ans": "сергей бондарчук",
     "variants": ["Федор Бондарчук", "Сергей Бондарчук", "Эльдар Рязанов", "Андрей Тарковский"],
     "score": 1
     }]
user_data = dict()
markup = None


def get_question(user_id: int):
    global markup
    markup = None
    user_index: list = user_data[user_id]["indexes"]
    if not user_index:
        user_data.pop(user_id)
        requests.put(f"{API_PREFIX}/stop", params={"tg_id": user_id})
        return "Вопросы закончились!!!"
    else:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        batons = [types.KeyboardButton(el) for el in QUESTIONS[user_index[0]]["variants"]]
        markup.add(*batons)
        return QUESTIONS[user_index[0]]["question"]


def ans_question(user_id: int, ans) -> str:
    user_index: list = user_data[user_id]["indexes"]
    question_now = QUESTIONS[user_index[0]]
    user_index.pop(0)
    if ans == question_now["ans"]:
        requests.put(f"{API_PREFIX}/score",
                     params={"delta": question_now["score"], "tg_id": user_id})
        return f"Правильный ответ, вы заработали {question_now['score']} баллов."
    else:
        return "Неправильный ответ :("


def create_name(user_id: int, name: str):
    requests.post(f"{API_PREFIX}/add_user", params={"tg_id": user_id, "name": name}).json()
    user_data[user_id]["status"] = "password"
    return "Имя успешно сохранено"


def get_password(user_id: int, password: str):
    if PASSWORD == password:
        user_data[user_id]["status"] = "question"
        return "Время начать викторину!"
    return "Неверный код!!!"


def init_game(done: bool, score: int | None, user_id: int):
    if score is None:
        # Начинаем игру если еще нет рекорда
        indexes = [el for el in range(len(QUESTIONS))]
        random.shuffle(indexes)
        user_data[user_id] = {"indexes": indexes, "status": "get_name"}
        return "Введите свое имя и фамилию"
    if isinstance(score, int):
        return_string = f"Вы уже {'играли и ' if done else ''}набрали {score} "
        if 10 <= score <= 20:
            return_string += "баллов."
        elif score % 10 == 1:
            return_string += "балл."
        elif score % 10 == 2 or score % 10 == 3:
            return_string += "балла."
        else:
            return_string += "баллов."
        return return_string


@bot.message_handler(commands=["start"])
def start_message(message: telebot.types.Message):
    user_id = message.from_user.id
    score, done = requests.get(f"{API_PREFIX}/init_score",
                               params={"tg_id": user_id}).json()
    bot.send_message(message.chat.id, init_game(done, score, user_id))


@bot.message_handler()
def start_message(message: telebot.types.Message):
    global markup
    user_id = message.from_user.id
    if message.from_user.id not in user_data:
        bot.send_message(message.chat.id, "Напишите команду /start чтобы начать.",
                         reply_markup=types.ReplyKeyboardRemove())
        return
    ans = message.text.lower().strip()
    if user_data[user_id]["status"] == "get_name":
        bot.send_message(message.chat.id, create_name(user_id, ans),
                         reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, "Введите код с доски",
                         reply_markup=types.ReplyKeyboardRemove())
    elif user_data[user_id]["status"] == "password":
        bot.send_message(message.chat.id, get_password(user_id, ans),
                         reply_markup=types.ReplyKeyboardRemove())
        if user_data[user_id]["status"] == "question":
            image_path = QUESTIONS[user_data[user_id]["indexes"][0]]["image"]
            question = get_question(user_id)
            if image_path is not None:
                image = open(image_path, 'rb')
                bot.send_photo(message.chat.id, image)
            bot.send_message(message.chat.id, question, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, ans_question(user_id, ans),
                         reply_markup=types.ReplyKeyboardRemove())
        question = get_question(user_id)
        if question != "Вопросы закончились!!!":
            image_path = QUESTIONS[user_data[user_id]["indexes"][0]]["image"]
            if image_path is not None:
                image = open(image_path, 'rb')
                bot.send_photo(message.chat.id, image)
        bot.send_message(message.chat.id, question, reply_markup=markup)


if __name__ == '__main__':
    bot.polling()
