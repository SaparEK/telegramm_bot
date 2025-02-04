from flask import Flask, request
import telebot
import os
import psycopg2
from telebot import types

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

# Инициализация Flask и бота
app = Flask(__name__)
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных
Database = os.getenv("DATABASE_URL")  # Используйте переменную окружения для безопасности

# Глобальные переменные
LANGUAGE = None
Name = None

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    conn = psycopg2.connect(Database)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR(50), phone VARCHAR(50))')
    cur.execute('CREATE TABLE IF NOT EXISTS admins (id SERIAL PRIMARY KEY, chat_id int)')
    conn.commit()
    cur.close()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('ru 🇷🇺', callback_data='ru')
    btn2 = types.InlineKeyboardButton('en 🇬🇧', callback_data='en')
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, 'Выберите язык / Choose a language', reply_markup=markup)

# Обработчик выбора языка
@bot.callback_query_handler(func=lambda call: call.data in ['ru', 'en'])
def handle_language_selection(call):
    global LANGUAGE
    LANGUAGE = call.data
    bot.send_message(call.message.chat.id, 'Вы выбрали русский язык! ✅' if LANGUAGE == 'ru' else 'You selected English! ✅')
    show_main_menu(call.message)

# Показ главного меню
def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_popular_questions = types.KeyboardButton('Популярные вопросы ❓' if LANGUAGE == 'ru' else 'Popular Questions ❓')
    btn_contact_operator = types.KeyboardButton('Связаться с оператором 👨‍💻' if LANGUAGE == 'ru' else 'Contact Operator 👨‍💻')
    btn_website = types.KeyboardButton('Веб-сайт 🌐' if LANGUAGE == 'ru' else 'Website 🌐')
    markup.add(btn_popular_questions, btn_contact_operator, btn_website)

    greeting = 'Выберите действие:' if LANGUAGE == 'ru' else 'Choose an action:'
    bot.send_message(message.chat.id, greeting, reply_markup=markup)

# Обработчик связи с оператором
@bot.message_handler(func=lambda message: message.text in ['Связаться с оператором 👨‍💻', 'Contact Operator 👨‍💻'])
def handle_contact_operator(message):
    bot.send_message(message.chat.id, 'Продолжая вы даете согласие на обработку персональных данных. ✅ \n\nКак к вам обращаться? 📝' if LANGUAGE == 'ru' else 'By continuing, you consent to the processing of personal data.✅ \n\nHow should I address you? 📝')
    bot.register_next_step_handler(message, user_name)

# Обработчик имени пользователя
def user_name(message):
    global Name
    Name = message.text.strip()
    bot.send_message(message.chat.id, 'Введите контактный номер телефона для звонка 📱:' if LANGUAGE == 'ru' else 'Enter your contact phone number 📱:')
    bot.register_next_step_handler(message, phone)

# Обработчик номера телефона
def phone(message):
    phone = message.text.strip()
    conn = psycopg2.connect(Database)
    bot.send_message(message.chat.id, 'Ваш запрос принят на обработку! В ближайшее время c вами свяжется один из наших менеджеров! ✅' if LANGUAGE == 'ru' else 'Your request has been processed! One of our managers will contact you soon! ✅')
    c = conn.cursor()
    c.execute("INSERT INTO users (name, phone) VALUES (%s, %s)", (Name, phone))
    c.execute("SELECT chat_id FROM admins")
    admins = c.fetchall()
    conn.commit()
    c.close()
    conn.close()

    for admin in admins:
        bot.send_message(admin[0], f'Новый клиент! Его телефон: {phone} и имя {Name}')

# Обработчик популярных вопросов
@bot.message_handler(func=lambda message: message.text in ['Популярные вопросы ❓', 'Popular Questions ❓'])
def show_popular_questions(message):
    markup = types.InlineKeyboardMarkup()
    questions = [
        ('Какие виды грузов вы перевозите?', 'What types of cargo do you transport?'),
        ('Как рассчитывается стоимость перевозки?', 'How is the cost of transportation calculated?'),
        ('Какие документы нужны для международной перевозки?', 'What documents are needed for international transportation?'),
        ('Как отследить груз?', 'How to track the shipment?'),
        ('В какие страны осуществляются перевозки?', 'Which countries are transported to?'),
        ('Сколько времени занимает доставка?', 'How long does the delivery take?'),
        ('Предоставляете ли вы услуги страхования груза?', 'Do you provide cargo insurance services?'),
        ('Как организована таможенная очистка груза?', 'How is customs clearance organized?')
    ]

    for idx, (ru_text, en_text) in enumerate(questions, start=1):
        question_text = ru_text if LANGUAGE == 'ru' else en_text
        markup.add(types.InlineKeyboardButton(question_text, callback_data=f'question_{idx}'))

    bot.send_message(message.chat.id, 'Выберите вопрос:' if LANGUAGE == 'ru' else 'Choose a question:', reply_markup=markup)

# Обработчик ответов на вопросы
@bot.callback_query_handler(func=lambda call: call.data.startswith('question_'))
def handle_question_answer(call):
    question_id = int(call.data.split('_')[1])
    answers = [
        ('Любые грузы (ТНП, хозтовары, негабаритные грузы).', 'Any cargo (consumer goods, household goods, oversized cargo).'),
        ('Расчёт индивидуально на каждый груз.', 'Calculation is made individually for each cargo.'),
        ('Инвойс, упаковочный лист, ТТН, контракт, разрешительные документы на груз, если таковые требуются.', 'Invoice, packing list, waybill, contract, and permits for the cargo, if required.'),
        ('Не отслеживается.', 'Not tracked.'),
        ('Транзит в любые страны.', 'Transit to any countries.'),
        ('Рассчитывается индивидуально.', 'Calculated individually.'),
        ('По требованию клиента.', 'Upon client request.'),
        ('Таможенной очисткой не занимаемся, только транзит.', 'We do not handle customs clearance, only transit.')
    ]
    answer = answers[question_id - 1][0] if LANGUAGE == 'ru' else answers[question_id - 1][1]
    bot.send_message(call.message.chat.id, answer)

# Обработчик команды /add_admin
@bot.message_handler(commands=['add_admin'])
def add_admin(message):
    conn = psycopg2.connect(Database)
    c = conn.cursor()
    c.execute("INSERT INTO admins (chat_id) VALUES (%s)", (message.chat.id,))
    conn.commit()
    c.close()
    conn.close()
    bot.send_message(message.chat.id, 'Менеджер добавлен')

# Обработчик команды /delete_admin
@bot.message_handler(commands=['delete_admin'])
def delete_admin(message):
    conn = psycopg2.connect(Database)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE chat_id = %s", (message.chat.id,))
    conn.commit()
    c.close()
    conn.close()
    bot.send_message(message.chat.id, 'Менеджер удален')

# Обработчик команды /website
@bot.message_handler(func=lambda message: message.text in ['Веб-сайт 🌐', 'Website 🌐'])
def open_website(message):
    url = 'https://ttkz-zbfg.vercel.app/'  # Замените на ваш URL
    bot.send_message(message.chat.id, 'Перейдите на наш сайт по ссылке ниже:' if LANGUAGE == 'ru' else 'Visit our website using the link below:')
    bot.send_message(message.chat.id, url)

# Обработчик входящих запросов от Telegram
@app.route("/", methods=["POST"])
def webhook():
    # Логируем входящий запрос
    print("Incoming request:", request.json)

    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        print("Decoded update:", update)

        # Обрабатываем обновление
        bot.process_new_updates([update])
    except Exception as e:
        print("Error processing update:", e)
    return "OK", 200

# Запуск приложения
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)