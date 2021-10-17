from numpy.core.numeric import True_
from telebot import types
import telebot
import pandas as pd

TOKEN = '2055887770:AAFtVI8ZgAjDLIvcpig6Aei6gpih-p7Ux3Y'
bot = telebot.TeleBot(TOKEN)


columns = ['price_doc', 'id', 'timestamp', 'full_sq', 'life_sq', 'floor', 'max_floor', 'material',
            'build_year', 'num_room', 'kitch_sq', 'state', 'product_type', 'sub_area'            
]
columns_request = columns.copy()

query_string = ''

new_content = {}

instruction = '''
    1. price_doc: sale price (this is the target variable)
    2. id: transaction id
    3. timestamp: date of transaction
    4. full_sq: total area in square meters, including loggias, balconies and other non-residential areas
    5. life_sq: living area in square meters, excluding loggias, balconies and other non-residential areas
    6. floor: for apartments, floor of the building
    7. max_floor: number of floors in the building
    8. material: wall material
    9. build_year: year built
    10. num_room: number of living rooms
    11. kitch_sq: kitchen area
    12. state: apartment condition
    13. product_type: owner-occupier purchase or investment
    14. sub_area: name of the district
'''

df = pd.read_csv('train.csv', sep=',')[columns]
df = df.astype(str)


@bot.message_handler(commands='start')
def send_keybord(message, text='Привет, чем могу помочь?'):
    global columns_request, query_string
    columns_request, query_string  = columns.copy(), ''
    keyboard = types.ReplyKeyboardMarkup(row_width=2)
    item1 = types.KeyboardButton('Запрос цены')
    item2 = types.KeyboardButton('Предоставление данных о продаже')
    keyboard.add(item1, item2)
    msg = bot.send_message(message.from_user.id, text=text, reply_markup=keyboard)
    bot.register_next_step_handler(msg, callback_worker)


@bot.message_handler(content_types=['text'])
def send_keybord(message):
    bot.send_message(message.from_user.id, text='Ой ой, я таких команд не знаю, введите /start')


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    global columns_request, query_string
    if call.text in ['Запрос цены', 'Продолжаем вводить']:
        if call.text == 'Запрос цены':
            bot.send_message(call.chat.id, text=f'Сперва ознакомьтесь с полями\n\n{instruction}')
        if call.text == 'Продолжаем вводить':
            query_string += 'and'
        keyboard = types.ReplyKeyboardMarkup(row_width=3)
        for c in columns_request:
            keyboard.add(types.KeyboardButton(c))
        msg = bot.send_message(call.chat.id, text='Вводите постепенно параметры', reply_markup=keyboard)
        bot.register_next_step_handler(msg, callback_worker)
    elif call.text in columns:
        columns_request.remove(call.text)
        query_string += ' ' + call.text
        msg = bot.send_message(call.chat.id, text=f'Введите значение')
        bot.register_next_step_handler(msg, set_value)
    elif call.text == 'Вывести':
        a = types.ReplyKeyboardRemove()
        msg = bot.send_message(call.chat.id, 'Выводим...', reply_markup=a)
        for data in df.query(query_string).values:
            string = ''
            for i, value in enumerate(data):
                string += columns[i] + ': ' + value + '\n'
            bot.send_message(call.chat.id, text=f'{string}')            
    elif call.text == 'Предоставление данных о продаже':
        global columns_add
        columns_add = columns.copy()
        # if message.text == "Wunderlist":
        a = types.ReplyKeyboardRemove()
        msg = bot.send_message(call.chat.id, 'Введите данные для добавления в БД', reply_markup=a)
        bot.send_message(call.chat.id, f'({15 - len(columns_add)}/14) price_doc:')
        bot.register_next_step_handler(msg, set_data)
    elif call.text in ['Закончить', 'Не надо']:
        bot.send_message(call.chat.id, text=f'Возвращайтесь скорей :)')
    else:
        bot.send_message(call.chat.id, text='Вы ввели что то не то, начните заново /start')

def set_data(message):
    global columns_add, df
    new_content[columns_add[0]] = message.text
    columns_add.pop(0)
    if len(columns_add) == 0:
        # bot.send_message(message.chat.id, text=f'Мы всё учли :)')
        try:
            a = float(new_content['price_doc'])
        except:
            new_content['price_doc'] = str(df['price_doc'].astype(float).mean())
            bot.send_message(message.chat.id, text=f'Упс, вы кажется ввели что-то не то в price_doc, поэтому мы заменили на среднее')
        string = ''
        for key, value in new_content.items():
            string += key + ': '+  value + '\n'
        bot.send_message(message.chat.id, text=f'{string}')
        df2 = df.copy()
        df = df2.append(new_content, ignore_index=True).copy()
        bot.send_message(message.chat.id, text=f'Мы всё учли, и добавили в БД :)')
        del df2
    
    else:
        # print(new_content)
        msg = bot.send_message(message.chat.id, f'({15 - len(columns_add)}/14) {columns_add[0]}:')
        bot.register_next_step_handler(msg, set_data)

        

def set_value(message):
    global query_string, df
    query_string += '== "' + message.text + '" '
    cnt = df.query(query_string).shape[0]
    try:
        avg_price = df.query(query_string)['price_doc'].astype(float).mean()
    except:
        avg_price = 'не получилось посчитать, есть проблемы с данными'
    if cnt <= 10:
        msg = bot.send_message(message.from_user.id, text=f'Получилось собрать достаточное количество наблюдений для вывода: {cnt}, средний прайс: {avg_price}')
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        keyboard.add(types.KeyboardButton('Вывести'), types.KeyboardButton('Не надо'))
        msg = bot.send_message(message.from_user.id, text='Что делаем дальше?', reply_markup=keyboard)
        bot.register_next_step_handler(msg, callback_worker)
    else:
        msg = bot.send_message(message.from_user.id, text=f'Получилось {cnt} наблюдений, их средняя цена {avg_price}, давайте сузим область запроса')
        keyboard = types.ReplyKeyboardMarkup(row_width=2)
        keyboard.add(types.KeyboardButton('Продолжаем вводить'), types.KeyboardButton('Закончить'))

        msg = bot.send_message(message.from_user.id, text='Что делаем дальше?', reply_markup=keyboard)
        bot.register_next_step_handler(msg, callback_worker)
    
bot.polling(none_stop=True)

