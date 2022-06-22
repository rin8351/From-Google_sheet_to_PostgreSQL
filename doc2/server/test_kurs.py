import psycopg2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import xml.etree.ElementTree as ET
import os
import datetime
import time

# Счетчик времени для выполнения задач- постоянной работы скрипта,
#  ежедневного обновления курса валюты с сайта ЦБРФ,
#  а также для отправки сообщения в телеграм
t30 = 0
t3600 = 0


# функция добавления в текстовый файл нового курса валюты
# если нового курса еще нет на сайте, то берется курс за сегодня
def dobavlenie_kursa(root):
    if root.findall('Valute') == []:
        today = datetime.date.today()
        d = today.strftime("%d/%m/%Y")
        root = get_root(d)
    for valute in root.findall('Valute'):
        if valute.get('ID') == 'R01235':
            new_kurs = valute.find('Value').text
    return new_kurs


# функция получения данных со страницы ЦБРФ.
# В нее передается дата в формате дд/мм/гггг
def get_root(d):
    url = 'https://www.cbr.ru/scripts/XML_daily.asp?date_req='+d
    response = requests.get(url)
    root = ET.fromstring(response.content)
    return root


# Функция для создания таблицы kurs, если ее не существует в базе PostgreSQL
def create_table():
    print('create')
    conn = psycopg2.connect(
        dbname=os.environ.get('POSTGRES_DB', ''),
        user=os.environ.get('POSTGRES_USER', ''),
        password=os.environ.get('POSTGRES_PASSWORD', ''),
        host=os.environ.get('POSTGRES_HOST', ''),
        )
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS kurs
                (№ INTEGER, number INTEGER, price_dol INTEGER,
                    date DATE, price_rub INTEGER)")
    conn.commit()
    conn.close()


def main():

    create_table()

    global data

    # подключаемся к гугл таблице
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
        ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'test-kurs1-1aee0139edd0.json', scope)
    gc = gspread.authorize(credentials)
    wks = gc.open("Copy_test").sheet1

    # получаем данные из гугл таблицы
    data = wks.get_all_values()

    # подключаемся к базе, используя реальные имя базы. пользователя и пароль

    conn = psycopg2.connect(
        dbname=os.environ.get('POSTGRES_DB', ''),
        user=os.environ.get('POSTGRES_USER', ''),
        password=os.environ.get('POSTGRES_PASSWORD', ''),
        host=os.environ.get('POSTGRES_HOST', ''),
        )
    cursor = conn.cursor()

    # удаление данных из таблицы в постгре
    cursor.execute("""DELETE FROM "kurs" """)
    conn.commit()

    # чтение из файла и заполнение словаря с курсами валют
    kurs_d = {}
    # если файла нет, заполняем его по новой, на те даты,
    # что есть в файле гугл таблицы
    if not os.path.exists('k.txt'):
        for i in data:
            if i == data[0]:
                pass
            else:
                d = i[3].replace('.', '/')
                kurs_d[d] = dobavlenie_kursa(get_root(d))
        with open('k.txt', 'w') as f:
            for key, value in kurs_d.items():
                f.write(key + ' ' + value + '\n')
    else:
        with open('k.txt', 'r') as f:
            for line in f:
                key, value = line.split()
                kurs_d[key] = value

    # расчет рублевой стоимости и добавление цены в таблицу из гугла
    for i in data:
        if i == data[0]:
            pass
        else:
            d = i[3]
            d = d.replace('.', '/')
            # если в текстовом файле нет нужного курса,
            # он берется с сайта ЦБРФ
            if d not in kurs_d:
                kurs_d[d] = dobavlenie_kursa(get_root(d))
            k = kurs_d[d]
            k = k.replace(',', '.')
            rub = float(k) * int(i[2])
            i.append(round(rub, 2))

    # заполняем таблицу POstgreSQL данными из списка data
    for row in data[1:]:
        cursor.execute("""SET datestyle = dmy; INSERT INTO "kurs"
                        (№, "number", "price_dol",  "date", "price_rub")
                        VALUES (%s, %s, %s, %s, %s)""", row)

    # сохраняем изменения
    conn.commit()

    # закрываем соединение
    cursor.close()
    conn.close()

    # запись курсов в текстовый файл
    with open('k.txt', 'w') as f:
        for key, value in kurs_d.items():
            f.write(key + ' ' + value + '\n')
    return kurs_d


# функция для ежедневного обновления курса валюты на завтрашний день,
# в 16 часов и запись в текстовый файл k.txt
def new_kurs_from_site(kurs_d):
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    d = tomorrow.strftime("%d/%m/%Y")
    now = datetime.datetime.now()
    if now.hour == 16:
        kurs_d[d] = dobavlenie_kursa(get_root(d))
        with open('k.txt', 'w') as f:
            for key, value in kurs_d.items():
                f.write(key + ' ' + value + '\n')


# функция для проверки соблюдения срока поставки.
# каждый день в 8 часов проверяется наличие заказов с датой поставки,
# соответствующих сегодняшней дате
def check_date():
    num_of_date = []
    now = datetime.datetime.now()
    if now.hour == 8:
        # словарь для хранения номеров заказов и их дат поставки
        list_of_orders = {}
        for i in data:
            if i == data[0]:
                pass
            else:
                d = i[3]
                d = d.replace('.', '/')
                # заполняем словарь номеров заказов и дат поставки
                list_of_orders[d] = i[1]
        today = datetime.date.today()
        d = today.strftime("%d/%m/%Y")
        if d in list_of_orders:
            num_of_date = list_of_orders[d]
    return num_of_date

# функция для отправки сообщений телеграмм боту
token = ''  # токен для доступа к боту
chat_id = ''  # id пользователя для отправки сообщений


def send_message(text):
    url = 'https://api.telegram.org/bot{}/sendMessage'.format(token)
    data = {'chat_id': chat_id, 'text': text}
    requests.post(url, data=data)


# отсчет времени для всех функций
while True:
    t30 += 1
    t3600 += 1
    # каждые 30 секунд происходит подключение к гугл таблице,
    # перерасчет рублевой стоимости,
    # а также перенос данных в базу PostgreSQL
    if t30 > 30:
        kurs_d = main()
        t30 = 0
    # каждый час происходит проверка времени. Когда наступает 16 часов,
    # курс валюты за завтрашний день вносится в текстовый файл k.txt
    # в 8 часов проверяется наличие заказов с истекшим сроком поставки,
    # и при наличии отправляется сообщение об этом в бот телеграмм
    if t3600 > 3600:
        new_kurs_from_site(kurs_d)
        num_of_date = check_date()
        if num_of_date != []:
            send_message(
                'Срок поставки заказа номер ' +
                num_of_date[0] + ' истекает!')
        t3600 = 0
    time.sleep(1)
