import os
import psycopg2
import requests
import telebot
from telebot import types

bot = telebot.TeleBot(os.getenv('TOKEN'))

def init_system():
    conn = psycopg2.connect(os.getenv("POSTGRES_CONN"))
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY AUTOINCREMENT ,
        username VARCHAR(255) UNIQUE NOT NULL,
        login VARCHAR(255),
        password VARCHAR(255)
    );''')

@bot.message_handler(commands=['start'])
def start_command(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Открыть меню', callback_data='main_menu_return'))
    bot.send_message(message.chat.id, '''Привет! Это бот для автоматического решения тестов из сервиса СДАМГИА. 
    Сейчас бот написан за 2 дня, находится в бета-тестировании и хостится лично мной. 
    В будущем если проект окажется восстребованым я постараюсь его улучшить и поставить на хостинг. 
    С любыми проблема пишите мне в лс @tiver211
    Для начала работы пропишите /menu или нажмите кнопку ниже
    PS: Пока что доступно только впр по математике за 8 класс, 
    перебор их базы данных не самый простой процесс, проявите терпение)''', reply_markup=keyboard)


bot.callback_query_handler(func= lambda call: call.data == "main_menu_return")
def main_menu_return(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Открыть меню', callback_data='main_menu_return'))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Меню", reply_markup=keyboard)

def login_test(login, password):
    ans = requests.post("https://math8-vpr.sdamgia.ru/newapi/login", json={"guest": False, "password": password, "user": login})
    if ans.status_code != 200:
        return False

    if ans.json()["status"] is not True:
        return False

    return True