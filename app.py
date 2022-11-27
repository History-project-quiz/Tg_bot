import os
import random

import telebot
from dotenv import load_dotenv
import requests

load_dotenv()
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN"))
QUESTIONS = [{"question": "Ответь 1", "ans": "1", "score": 10},
             {"question": "Ответь 2", "ans": "2", "score": 5},
             {"question": "Ответь 3", "ans": "3", "score": 6},
             {"question": "Ответь 4", "ans": "4", "score": 7},
             {"question": "Ответь 5", "ans": "5", "score": 2}]
user_questions = dict()


def get_question(user_id: int):
    index = user_questions[user_id]["indexes"][0]
    return QUESTIONS[index]["question"]


def init_game(done: bool, score: int | None, user_id: int):
    if score is None:
        indexes = [el for el in range(len(QUESTIONS))]
        random.shuffle(indexes)
        user_questions[user_id] = {"indexes": indexes}
        return get_question(user_id)
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
    user_data = message.from_user
    first_name = user_data.first_name if user_data.first_name is not None else ''
    last_name = user_data.last_name if user_data.last_name is not None else ''
    user_name = f"{first_name} {last_name}"
    user_id = user_data.id
    score, done = requests.get("http://127.0.0.1:8000/init_score",
                               params={"tg_id": user_id, "name": user_name}).json()
    bot.send_message(message.chat.id, init_game(done, score, user_id))


@bot.message_handler()
def start_message(message: telebot.types.Message):
    if message.from_user.id not in user_questions:
        bot.send_message(message.chat.id, "Напишите команду /start чтобы начать.")
        return
    ans = message.text.lower().strip()
    user_index: list = user_questions[message.from_user.id]["indexes"]
    question_now = QUESTIONS[user_index[0]]
    if ans == question_now["ans"]:
        bot.send_message(message.chat.id,
                         f"Правильный ответ, вы заработали {question_now['score']} баллов.")
        requests.put("http://127.0.0.1:8000/score",
                     params={"delta": question_now["score"], "tg_id": message.from_user.id})
    else:
        bot.send_message(message.chat.id, "Неправильный ответ :(")
    user_index.pop(0)
    if not user_index:
        user_questions.pop(message.from_user.id)
        bot.send_message(message.chat.id, "Вопросы закончились!!!")
        requests.put("http://127.0.0.1:8000/stop", params={"tg_id": message.from_user.id})
    else:
        bot.send_message(message.chat.id, get_question(message.from_user.id))


if __name__ == '__main__':
    bot.polling()
