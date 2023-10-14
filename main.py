import sqlite3
import telebot
from collections import Counter
from telebot import types



TOKEN = '6570715645:AAEuolZUT27VHELYQAYExXpZA0pVXiwOcnY'

conn = sqlite3.connect("birds.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS seen_birds (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        bird_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (bird_id) REFERENCES birds (id)
    )
''')


cursor.execute('''
    CREATE TABLE IF NOT EXISTS bird_sightings (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        bird_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (bird_id) REFERENCES birds (id)
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sightings (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        bird_id INTEGER
    )
''')
conn.commit()

bot = telebot.TeleBot(TOKEN)

birds = {}

@bot.message_handler(commands=['create'])
def start(message):
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(message.chat.id, "Привет! Я помогу вам создать запись о птице. Пожалуйста, введите имя птицы:", reply_markup=markup)
    bot.register_next_step_handler(message, ask_name)
@bot.callback_query_handler(func=lambda call: call.data.startswith('seen_bird_'))
def seen_bird_callback(call):
    chat_id = call.message.chat.id
    bird_id = call.data.split('_')[2]
    user_id = call.from_user.id

    if chat_id in birds and 'seen' in birds[chat_id] and bird_id in birds[chat_id]['seen']:
        bot.answer_callback_query(call.id, "Вы уже отметили, что видели эту птицу.")
    else:
        if chat_id not in birds:
            birds[chat_id] = {'seen': []}

        birds[chat_id]['seen'].append(bird_id)
        bot.answer_callback_query(call.id, "Вы отметили, что видели эту птицу.")

        update_bird_info_message(chat_id, bird_id)

def update_bird_info_message(chat_id, bird_id):
    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM birds WHERE id = ?", (bird_id,))
    row = cursor.fetchone()

    if row:
        bird_id, name, color, photo_id = row

        if chat_id in birds and 'seen' in birds[chat_id] and bird_id in birds[chat_id]['seen']:
            bird_info = f"ID: {bird_id}\nИмя птицы: {name}\nЦвет перьев: {color}\n(Вы видели)"
        else:
            bird_info = f"ID: {bird_id}\nИмя птицы: {name}\nЦвет перьев: {color}"

        markup = types.InlineKeyboardMarkup()
        seen_button = types.InlineKeyboardButton("Я видел эту птицу", callback_data=f"seen_bird_{bird_id}")
        markup.row(seen_button)

        bot.send_photo(chat_id, photo_id, caption=bird_info, reply_markup=markup)

    conn.close()

def ask_name(message):
    chat_id = message.chat.id
    name = message.text
    birds[chat_id] = {'name': name}
    bot.send_message(chat_id, f"Отлично, имя птицы: {name}. Теперь введите цвет перьев:")
    bot.register_next_step_handler(message, ask_color)

def ask_color(message):
    chat_id = message.chat.id
    color = message.text
    birds[chat_id]['color'] = color
    bot.send_message(chat_id, f"Спасибо! Цвет перьев: {color}. Теперь пришлите фото птицы:")
    bot.register_next_step_handler(message, ask_photo)



def ask_photo(message):
    chat_id = message.chat.id

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    if message.photo:
        file_id = message.photo[-1].file_id
        birds[chat_id]['photo'] = file_id

        cursor.execute("INSERT INTO birds (name, color, photo_id) VALUES (?, ?, ?)",
                       (birds[chat_id]['name'], birds[chat_id]['color'], birds[chat_id]['photo']))
        conn.commit()

        cursor.execute("SELECT last_insert_rowid()")
        row = cursor.fetchone()
        bird_id = row[0]

        bot.send_photo(chat_id, birds[chat_id]['photo'], caption=f"ID: {bird_id}\nИмя птицы: {birds[chat_id]['name']}\nЦвет перьев: {birds[chat_id]['color']}")

        bot.send_message(chat_id, "Запись о птице создана и сохранена в базе данных. Спасибо.")
    else:
        bot.send_message(chat_id, "Пожалуйста, отправьте фото птицы.")
        bot.register_next_step_handler(message, ask_photo)

    conn.close()

@bot.message_handler(commands=['search'])
def search(message):
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(message.chat.id, "Введите ID птицы, которую вы хотите найти:", reply_markup=markup)
    bot.register_next_step_handler(message, find_bird_by_id)

def find_bird_by_id(message):
    chat_id = message.chat.id
    bird_id = message.text

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM birds WHERE id = ?", (bird_id,))
    row = cursor.fetchone()

    if row:
        bird_id, name, color, photo_id = row
        bot.send_photo(chat_id, photo_id, caption=f"ID: {bird_id}\nИмя птицы: {name}\nЦвет перьев: {color}")
    else:
        bot.send_message(chat_id, f"Птица с ID {bird_id} не найдена в базе данных.")

    conn.close()

    start(message)

@bot.message_handler(commands=['random'])
def random_bird(message):
    chat_id = message.chat.id

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM birds ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()

    if row:
        bird_id, name, color, photo_id = row
        bot.send_photo(chat_id, photo_id, caption=f"ID: {bird_id}\nИмя птицы: {name}\nЦвет перьев: {color}")

        markup = types.InlineKeyboardMarkup()
        seen_button = types.InlineKeyboardButton("Я видел эту птицу", callback_data=f"seen_{bird_id}")
        markup.row(seen_button)

        bot.send_message(chat_id, "Отметьте, если видели эту птицу:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "В базе данных нет записей о птицах.")

    conn.close()


from telebot import types







@bot.callback_query_handler(func=lambda call: call.data.startswith('bird_info_'))
def bird_info_callback(call):
    chat_id = call.message.chat.id
    bird_id = call.data.split('_')[2]
    user_id = call.from_user.id

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM birds WHERE id = ?", (bird_id,))
    row = cursor.fetchone()

    if row:
        bird_id, name, color, photo_id = row

        cursor.execute("SELECT seen FROM bird_sightings WHERE user_id = ? AND bird_id = ?", (user_id, bird_id))
        sighting = cursor.fetchone()

        if sighting:
            seen = sighting[0]

            if not seen:
                markup = types.InlineKeyboardMarkup()
                seen_button = types.InlineKeyboardButton("Я видел эту птицу", callback_data=f"seen_bird_{bird_id}")
                markup.row(seen_button)

                bot.send_photo(chat_id, photo_id, caption=f"ID: {bird_id}\nИмя птицы: {name}\nЦвет перьев: {color}", reply_markup=markup)
            else:
                bot.send_photo(chat_id, photo_id, caption=f"ID: {bird_id}\nИмя птицы: {name}\nЦвет перьев: {color}")
        else:
            bot.send_message(chat_id, "ВЫ еще не встречали эту птицу.")
    else:
        bot.send_message(chat_id, "Птица с ID {bird_id} не найдена в базе данных.")

    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('seen_'))
def seen_bird_callback(call):
    chat_id = call.message.chat.id
    bird_id = call.data.split('_')[1]

    user_id = call.from_user.id

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bird_sightings WHERE user_id = ? AND bird_id = ?", (user_id, bird_id))
    sighting = cursor.fetchone()

    if sighting:
        bot.answer_callback_query(call.id, "Вы уже отметили, что видели эту птицу.")
    else:
        cursor.execute("INSERT INTO bird_sightings (user_id, bird_id) VALUES (?, ?)", (user_id, bird_id))
        conn.commit()
        bot.answer_callback_query(call.id, "Вы отметили, что видели эту птицу.")

@bot.message_handler(commands=['birds'])
def list_seen_birds(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT birds.name, birds.color, birds.photo_id FROM birds INNER JOIN bird_sightings ON birds.id = bird_sightings.bird_id WHERE bird_sightings.user_id = ?", (user_id,))
    rows = cursor.fetchall()

    if rows:
        bot.send_message(chat_id, "Вы увидели следующие птицы:")
        for row in rows:
            name, color, photo_id = row
            bird_info = f"Имя птицы: {name}\nЦвет перьев: {color}"
            bot.send_photo(chat_id, photo_id, caption=bird_info)
    else:
        bot.send_message(chat_id, "Вы пока не видели ни одной птицы.")

    conn.close()


@bot.message_handler(commands=['list_all_birds'])
def list_all_birds(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    conn = sqlite3.connect("birds.db")
    cursor = conn.cursor()

    cursor.execute("SELECT birds.id, birds.name, bird_sightings.user_id IS NOT NULL AS seen FROM birds LEFT JOIN bird_sightings ON birds.id = bird_sightings.bird_id AND bird_sightings.user_id = ?", (user_id,))
    rows = cursor.fetchall()

    if rows:
        user_info = f"Профиль пользователя {message.from_user.username}:\nКоличество птиц которых вы успели заметить: {len(rows)}"
        bot.send_message(chat_id, user_info)
        for row in rows:
            bird_id, name, seen = row
            if seen:
                markup = types.InlineKeyboardMarkup()
                bird_info_button = types.InlineKeyboardButton("Карточка птицы", callback_data=f"bird_info_{bird_id}")
                markup.row(bird_info_button)

                bird_info = f"[ID: {bird_id}, Имя: {name} , вы ее видели]"
                bot.send_message(chat_id, bird_info, reply_markup=markup)
            else:
                bird_info = f"[id {bird_id}, {name}] Найдите эту птицу чтобы увидеть ее карточку"
                bot.send_message(chat_id, bird_info)
    else:
        bot.send_message(chat_id, "В базе данных нет записей о птицах.")

    conn.close()



if __name__ == '__main__':
    bot.polling(none_stop=True)
