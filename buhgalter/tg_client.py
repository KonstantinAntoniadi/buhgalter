from sqlalchemy import false
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import uuid
from telebot import types
from decimal import Decimal
from datetime import datetime
from modules.pg_module import PgModule
import pytz
import calendar


from modules.vault_client import *
from creds.login_data import *


class TgOperationData():
    def __init__(self, id):
        self.id = id
        self.bank_name = None
        self.status = 'OK'
        self.type = None
        self.group = None
        self.value: Decimal = None
        self.currency = 'rub'
        self.brand_name = None
        self.category = None
        self.cashback: Decimal = 0
        self.is_between_owner_accounts = false
        self.created_at = None
        self.raw = {}


vault_client = VaultClient(VAULT_URL, VAULT_ROOT_TOKEN)

ALLOWED_CHAT_ID = vault_client.get_chat_id()

user_states = {
    # ALLOWED_CHAT_ID:
}

user_operation_states = {
    ALLOWED_CHAT_ID: []
}


tz = pytz.timezone('Europe/Moscow')  # UTC+3
bot = telebot.TeleBot(vault_client.get_tg_token())


pg_module = PgModule(
    db_user=vault_client.get_db_user(),
    db_password=vault_client.get_db_password(),
    db_host=vault_client.get_db_host(),
    db_port=vault_client.get_db_port(),
    db_name=vault_client.get_db_name(),
)


def start_menu():
    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton('Добавить операцию')
    btn2 = types.KeyboardButton('Посмотреть баланс')
    btn3 = types.KeyboardButton('Редактировать наличные')
    btn4 = types.KeyboardButton('Посмотреть операции')
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)

    return markup


@bot.message_handler(commands=['start'])
def start(message):
    global operation_id_for_change
    operation_id_for_change = ''
    user_id = message.chat.id
    user_states[user_id] = 'DEFAULT'
    bot.send_message(ALLOWED_CHAT_ID, 'Hello', reply_markup=start_menu())


def new_operation_type_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Пополнение'))
    markup.add(types.KeyboardButton('Трата'))
    return markup


MONTHS = ["Январь", "Февраль", "Март",
          "Апрель", "Май", "Июнь",
          "Июль", "Август", "Сентябрь",
          "Октябрь", "Ноябрь", "Декабрь"]


def view_month_type_menu():
    markup = types.ReplyKeyboardMarkup()
    markup.row_width = 3
    for month in MONTHS:
        markup.add(types.KeyboardButton(month))

    return markup


def view_operation_type_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Пополнения'))
    markup.add(types.KeyboardButton('Траты'))
    return markup


ALLOWED_BANKS = ['sber', 'ozon', 'wb', 'cash']


def bank_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('sber')
    btn2 = types.KeyboardButton('ozon')
    btn3 = types.KeyboardButton('wb')
    markup.row(btn1, btn2, btn3)
    btn4 = types.KeyboardButton('cash')
    markup.row(btn4)
    return markup


CREDIT_CATEGORIES = ['Подарок', 'Зарплата', 'Перевод за то, что я оплатил']
DEBIT_CATEGORIES = ['Фастфуд', 'Транспорт', 'Супермаркеты', 'Спорт',
                    'Салоны красоты и СПА', 'Рестораны и кафе', 'Одежда и обувь', 'Медицина и аптеки', 'Косметика',
                    'Аксессуары', 'Электронника', 'Дом и быт', 'Комиссия банка', 'Подарок', 'Путешествия']


def credit_categroy_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in CREDIT_CATEGORIES:
        markup.add(types.KeyboardButton(category))

    return markup


def debit_categroy_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Фастфуд')
    btn2 = types.KeyboardButton('Транспорт')
    btn3 = types.KeyboardButton('Супермаркеты')
    markup.row(btn1, btn2, btn3)
    btn4 = types.KeyboardButton('Спорт')
    btn5 = types.KeyboardButton('Салоны красоты и СПА')
    btn6 = types.KeyboardButton('Рестораны и кафе')
    markup.row(btn4, btn5, btn6)
    btn7 = types.KeyboardButton('Одежда и обувь')
    btn8 = types.KeyboardButton('Медицина и аптеки')
    btn9 = types.KeyboardButton('Косметика')
    markup.row(btn7, btn8, btn9)
    btn10 = types.KeyboardButton('Аксессуары')
    btn11 = types.KeyboardButton('Электронника')
    btn12 = types.KeyboardButton('Дом и быт')
    markup.row(btn10, btn11, btn12)
    btn13 = types.KeyboardButton('Комиссия банка')
    btn14 = types.KeyboardButton('Подарок')
    markup.row(btn13, btn14)

    return markup


MONTHS_TO_ORDER = {
    "Январь": 1,
    "Февраль": 2,
    "Март": 3,
    "Апрель": 4,
    "Май": 5,
    "Июнь": 6,
    "Июль": 7,
    "Август": 8,
    "Сентябрь": 9,
    "Октябрь": 10,
    "Ноябрь": 11,
    "Декабрь": 12
}

TYPE_TO_INNER_TYPE = {
    "Пополнения": 'credit',
    "Траты": "debit"
}


month_choose_data = [None, None, None]
operation_id_for_change = ''


callback_id_to_text = {}


# Создание инлайн-клавиатуры для операций и пагинации
def get_operations_markup(operations, current_page, total_pages):
    global callback_id_to_text
    keyboard = InlineKeyboardMarkup()
    for operation in operations:
        text_operation = f"{operation.value} ({operation.cashback}) {operation.category} {operation.created_at.strftime("%d-%m-%Y %H:%M:%S")}"
        callback_id = str(operation.id)
        callback_data = f"o_{callback_id}"
        callback_id_to_text[callback_id] = text_operation
        button = InlineKeyboardButton(
            text=text_operation, callback_data=callback_data)

        keyboard.add(button)

    # Кнопки навигации
    if current_page > 1:
        keyboard.add(InlineKeyboardButton(
            "Назад", callback_data=f"page_{current_page - 1}"))
    if current_page < total_pages:
        keyboard.add(InlineKeyboardButton(
            "Вперед", callback_data=f"page_{current_page + 1}"))
    return keyboard


def get_categories_markup(
):
    keyboard = []
    if month_choose_data[2] == 'credit':
        keyboard = [[InlineKeyboardButton(category, callback_data=f"c_{category}")]
                    for category in CREDIT_CATEGORIES]
    elif month_choose_data[2] == 'debit':
        keyboard = [[InlineKeyboardButton(category, callback_data=f"c_{category}")]
                    for category in DEBIT_CATEGORIES]
    return InlineKeyboardMarkup(keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global month_choose_data
    global callback_data_to_text
    global operation_id_for_change
    global callback_id_to_text

    if call.data.startswith("page_"):
        _, page_number = call.data.split("_")
        page_number = int(page_number)

        # user_id = call.from_user.id
        month_number = MONTHS_TO_ORDER[month_choose_data[0]]
        start = datetime(month_choose_data[1], month_number, 1)
        end = datetime(month_choose_data[1], month_number, calendar.monthrange(
            month_choose_data[1], month_number)[1])
        type_operations = month_choose_data[2]

        operations = pg_module.get_operations_by_period(
            start, end, type_operations)
        operations_per_page = 10
        total_pages = (len(operations) + operations_per_page -
                       1) // operations_per_page
        display_operations = operations[(
            page_number-1) * operations_per_page: page_number * operations_per_page]
        markup = get_operations_markup(
            display_operations, page_number, total_pages)
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id, text="Ваши операции:", reply_markup=markup)

    elif call.data.startswith("o_"):
        _, operation_id = call.data.split("_")
        operation_id_for_change = operation_id
        markup = get_categories_markup()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"Выберите новую категорию для операции {callback_id_to_text[operation_id]}:", reply_markup=markup)

    elif call.data.startswith("c_"):
        _, new_category = call.data.split("_")
        operation_id = operation_id_for_change
        try:
            pg_module.update_operation_category(operation_id, new_category)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"Категория операции {callback_id_to_text[operation_id]} изменена на {new_category}.")
        except Exception as e:
            bot.edit_message_text(chat_id=call.message.chat.id,
                                  message_id=call.message.message_id, text=f"Что-то пошло не так: {e}.")


def _format_money(money):
    return f"{money:,}".replace(",", " ")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global month_choose_data

    user_id = message.chat.id
    text = message.text
    if str(user_id) != str(ALLOWED_CHAT_ID):
        return

    state = user_states.get(user_id, 'DEFAULT')

    if state == 'DEFAULT':
        if message.text == 'Добавить операцию':
            user_states[user_id] = 'CHOOSE_OPERATION_TYPE'
            user_operation_states[user_id] = [TgOperationData(id=uuid.uuid4())]

            bot.send_message(message.chat.id, 'Выберите тип операции',
                             reply_markup=new_operation_type_menu())
        elif message.text == 'Посмотреть баланс':
            balance_rub = pg_module.get_balance('rub')
            balance_usd = pg_module.get_balance('usd')
            bot.send_message(
                message.chat.id, f"Баланс:\n{_format_money(balance_rub)} rub\n{_format_money(balance_usd)} usd")
        elif message.text == 'Посмотреть операции':
            user_states[user_id] = 'VIEW_OPERATIONS_CHOOSE_MONTH'
            bot.send_message(message.chat.id, 'Выберите месяц',
                             reply_markup=view_month_type_menu())
        elif message.text == 'Редактировать наличные':
            user_states[user_id] = 'EDIT_CASH'
            bot.send_message(message.chat.id, 'Введите актуальное число')
    elif state == 'CHOOSE_OPERATION_TYPE':
        if message.text in ['Пополнение', 'Трата']:
            if message.text == 'Пополнение':
                user_states[user_id] = 'OPERATION_TYPE_IS_CREDIT'
                user_operation_states[user_id][0].type = 'credit'
                user_operation_states[user_id][0].group = 'TRANSER'
                bot.send_message(user_id, "Выберите категорию:",
                                 reply_markup=credit_categroy_menu())
            elif message.text == 'Трата':
                user_states[user_id] = 'OPERATION_TYPE_IS_DEBIT'
                user_operation_states[user_id][0].type = 'debit'
                user_operation_states[user_id][0].group = 'PAY'
                bot.send_message(user_id, "Выберите категорию:",
                                 reply_markup=debit_categroy_menu())
            user_states[user_id] = 'CHOOSE_CATEGORY'
        else:
            bot.send_message(user_id, "Пожалуйста, выберите один из вариантов.",
                             reply_markup=new_operation_type_menu())

    elif state == 'CHOOSE_CATEGORY':
        user_operation_states[user_id][0].category = message.text
        user_states[user_id] = 'ENTER_AMOUNT'
        bot.send_message(user_id, "Введите сумму",
                         reply_markup=types.ReplyKeyboardRemove())

    elif state == 'ENTER_AMOUNT':
        try:
            amount = Decimal(message.text)
            user_operation_states[user_id][0].value = amount
            user_states[user_id] = 'CHOOSE_BANK'
            bot.send_message(user_id, "Выберите банк",
                             reply_markup=bank_menu())
        except Exception as e:
            bot.send_message(
                user_id, "Ердык пердык, сумму нормально ввести не можешь? Вводи по-новой")

    elif state == 'EDIT_CASH':
        try:
            amount = Decimal(message.text)
            pg_module.upsert_cache_account(amount)
            balance_cache = pg_module.get_cache_balance('rub')
            bot.send_message(
                message.chat.id, f"Баланс обновлен. Текущий баланс кэша: {_format_money(balance_cache)} rub")
            user_states[user_id] = 'DEFAULT'
        except Exception as e:
            bot.send_message(
                user_id, "Ердык пердык, сумму нормально ввести не можешь? Вводи по-новой")

    elif state == 'CHOOSE_BANK':
        bank = message.text
        if bank not in ALLOWED_BANKS:
            bot.send_message(
                user_id, "Ердык пердык, нажать на кнопку не можешь? Вводи руками теперь")

        user_operation_states[user_id][0].bank_name = bank
        user_states[user_id] = 'CHOOSE_DATE'
        bot.send_message(user_id, "Введите дату в формате dd.mm.yyyy",
                         reply_markup=types.ReplyKeyboardRemove())

    elif state == 'CHOOSE_DATE':
        try:
            date_obj = datetime.strptime(message.text, "%d.%m.%Y")
            date_obj = date_obj.replace(hour=12, minute=0, second=0)
            user_operation_states[user_id][0].created_at = tz.localize(
                date_obj)
            user_states[user_id] = 'DEFAULT'
            pg_module.add_operation_from_telegram(
                operation=user_operation_states[user_id][0])
            bot.send_message(user_id, "Запись успешно добавлена!",
                             reply_markup=start_menu())
        except Exception as e:
            bot.send_message(
                user_id, f"Что-то пошло не так: {e}", reply_markup=start_menu())

    # view operations
    elif state == 'VIEW_OPERATIONS_CHOOSE_MONTH':
        if text in MONTHS:
            month_choose_data = [
                text,
                2025,  # year
                None,  # type
            ]
            user_states[user_id] = 'VIEW_OPERATIONS_CHOOSE_TYPE_OPERATIONS'
            bot.send_message(user_id, "Выбери тип операции",
                             reply_markup=view_operation_type_menu())
        else:
            bot.send_message(
                user_id, "Ердык пердык, нажать на кнопку не можешь? Вводи руками теперь")

    elif state == 'VIEW_OPERATIONS_CHOOSE_TYPE_OPERATIONS':
        if text in ['Пополнения', 'Траты']:
            month_choose_data[2] = TYPE_TO_INNER_TYPE[text]
            month_number = MONTHS_TO_ORDER[month_choose_data[0]]
            start = datetime(month_choose_data[1], month_number, 1)
            end = datetime(month_choose_data[1], month_number, calendar.monthrange(
                month_choose_data[1], month_number)[1])

            operations = pg_module.get_operations_by_period(
                start, end, month_choose_data[2])

            operations_per_page = 10
            total_pages = (len(operations) +
                           operations_per_page - 1) // operations_per_page
            page_number = 1
            display_operations = operations[(
                page_number-1) * operations_per_page: page_number * operations_per_page]
            markup = get_operations_markup(
                display_operations, page_number, total_pages)
            bot.send_message(
                user_id, "Операции. Нажмите на кнопку, если нужно изменить категорию", reply_markup=markup)
        else:
            bot.send_message(
                user_id, "Ердык пердык, нажать на кнопку не можешь? Вводи руками теперь")

    else:
        bot.send_message(user_id, "nikuda ne popal")
        bot.send_message(message.chat.id, 'Шо то не то')


bot.polling(none_stop=True)
