import os
import time
from .sdamgia_hack.parser import *
import psycopg2
import requests
import telebot
from telebot import types
from telebot_dialogue import DialogueManager, Dialogue

bot = telebot.TeleBot(os.getenv('TOKEN'))
dialogue_manager = DialogueManager()

cursor = None
while cursor is None:
    try:
        conn = psycopg2.connect(os.getenv("POSTGRES_CONN"))
        cursor = conn.cursor()

    except psycopg2.OperationalError:
        time.sleep(1)


def init_system():
    hacker = ProblemHacker(bd_conn=os.getenv("POSTGRES_CONN"), name="math8-vpr", base_url="https://sdamgia.ru")
    print("hacking", flush=True)
    #hacker.hack_subj(Subj.from_url("https://math8-vpr.sdamgia.ru"))
    print("hacked", flush=True)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE NOT NULL,
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
    Код полностью открытый, вы можете просмотреть его по ссылке: https://github.com/Tiver211/sdamgia_hack 
    Для начала работы пропишите /menu или нажмите кнопку ниже
    P.S: Пока что доступно только впр по математике за 8 класс, 
    перебор их базы данных не самый простой процесс, проявите терпение ;)
    P.P.S: Пока решаются только тесты, у рно другие ссылки и разметка, мне под них придётся отдельно писать''', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "main_menu_return")
def main_menu_return(call: types.CallbackQuery):
    dialogue_manager.finish_dialogue(call.message.chat.id)
    menu = get_main_menu(call.message.chat.id)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, **menu)

@bot.callback_query_handler(func=lambda call: call.data == "login_button")
def login_button(call: types.CallbackQuery):
    dialogue = Dialogue(call.message.chat.id, get_user_login)
    dialogue_manager.add_dialogue(dialogue)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text="Введите логин")

@bot.message_handler(content_types=["text"])
def multi_handler(message):
    dialogue_manager.handle_message(message)

def get_user_login(message: types.Message, dialogue: Dialogue):
    login = message.text
    dialogue.update_context("login", login)
    dialogue.handler = get_user_password
    bot.send_message(chat_id=dialogue.user_id, text="Введите пароль")

def get_user_password(message: types.Message, dialogue: Dialogue):
    password = message.text
    login = dialogue.get_context("login")

    if login_test(login, password):
        login_user(dialogue.user_id, login, password)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Меню", callback_data="main_menu_return"))
        bot.send_message(dialogue.user_id, "Авторизация успешна",
                         reply_markup=keyboard)

    else:
        dialogue.handler = get_user_login
        bot.send_message(dialogue.user_id, "Данные некоректны, попробуйте ещё раз")

@bot.callback_query_handler(func=lambda call: call.data == "logout")
def logout_call(call: types.CallbackQuery):
    logout_user(call.message.chat.id)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, **get_main_menu(call.message.chat.id))

@bot.callback_query_handler(func=lambda call: call.data == "solve_test_button")
def solve_test_button(call: types.CallbackQuery):
    dialogue = Dialogue(call.message.chat.id, get_test_url)
    dialogue_manager.add_dialogue(dialogue)
    bot.edit_message_text("введите ссылку на тест, например: https://math8-vpr.sdamgia.ru/test?id=2530414", call.message.chat.id, call.message.id)


def get_test_url(message: types.Message, dialogue: Dialogue):
    url = message.text
    user_data = get_login(dialogue.user_id)
    if not user_data:
        bot.send_message(dialogue.user_id, "Ошибка ваших данных авторизации")
        return
    test = Test.from_url(url, *user_data)
    data = test.get_problems_answers()
    ans = "Ответы на все вопросы, вы можете сохранить и тогда после перехода по ссылке короткие ответы уже будут введены\n"
    print(data, flush=True)
    for problem in data.items():
        print(problem, flush=True)
        ans += f"{problem[0]}: Ответ: {problem[1][0]}, ссылка на решение: {problem[1][1]}\n"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Сохранить ответы", callback_data="save_answers:"+url))
    keyboard.add(types.InlineKeyboardButton("Меню", callback_data="main_menu_return"))
    bot.send_message(dialogue.user_id, ans, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_answers:"))
def save_answers(call: types.CallbackQuery):
    url = call.data.replace("save_answers:", "")
    user_data = get_login(call.message.chat.id)
    if not user_data:
        bot.send_message(call.message.chat.id, "Ошибка ваших данных авторизации")
        return
    test = Test.from_url(url, *user_data)
    data = test.solve()
    ans = "Нажмите кнопку ниже чтобы перейти к тесту с решеными заданиями с кратким ответом\n"
    for problem in data.items():
        ans += f"{problem[0]}: решение: {problem[1]}\n"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Открыть тест", url=test.continue_url))
    keyboard.add(types.InlineKeyboardButton("Меню", callback_data="main_menu_return"))
    bot.send_message(call.message.chat.id, ans, reply_markup=keyboard)

def get_main_menu(user_id):
    keyboard = types.InlineKeyboardMarkup()
    if get_login_status(user_id):
        keyboard.add(types.InlineKeyboardButton("Решить тест", callback_data="solve_test_button"))
        keyboard.add(types.InlineKeyboardButton("Выйти", callback_data="logout"))
        text = "Главное меню"

    else:
        text = ("Пожалуйста войдите в аккаунт sdamgia.ru, "
                "это нужно для просмотров тестов системой и автоввода ответов\n"
                "Данные вашей учетной записи будут удалены сразу при выходе")
        keyboard.add(types.InlineKeyboardButton("Авторизоваться", callback_data="login_button"))

    return {"text": text, "reply_markup": keyboard}

def get_login_status(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
    return bool(cursor.fetchone())

def get_login(user_id):
    cursor.execute("SELECT login, password FROM users WHERE user_id = %s", (user_id,))
    data = cursor.fetchone()
    if data is None:
        return False

    return data

def login_user(user_id, login, password):
    cursor.execute("INSERT INTO users (user_id, login, password) VALUES (%s, %s, %s)", (user_id, login, password))

def logout_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

def login_test(login, password):
    ans = requests.post("https://math8-vpr.sdamgia.ru/newapi/login", json={"guest": False, "password": password, "user": login})
    if ans.status_code != 200:
        return False

    if ans.json()["status"] is not True:
        return False

    return True