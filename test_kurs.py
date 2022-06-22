import psycopg2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import xml.etree.ElementTree as ET
import os
import datetime
import time

# Счетчик времени для выполнения двух задач- постоянной работы скрипта,
# а также для ежедневного обновления курса валюты с сайта ЦБРФ
t30 = 0
t3600 = 0


# функция добавления в текстовый файл нового курса валюты
def dobavlenie_kursa(root):
    if root.findall('Valute') == []: # если нового курса еще нет на сайте, то берется курс за сегодня
        today = datetime.date.today()
        d= today.strftime("%d/%m/%Y")
        root= get_root(d)
    for valute in root.findall('Valute'):
        if valute.get('ID') == 'R01235':
            new_kurs=valute.find('Value').text
    return new_kurs


# функция получения данных со страницы ЦБРФ. В нее передается дата в формате дд/мм/гггг
def get_root(d):
    url='https://www.cbr.ru/scripts/XML_daily.asp?date_req='+d
    response = requests.get(url)
    root = ET.fromstring(response.content)
    return root


def main():
    print('test')
    # подключаемся к гугл таблице
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'test-kurs1-1aee0139edd0.json', scope)
    gc = gspread.authorize(credentials)
    wks = gc.open("Copy_test").sheet1

    # получаем данные из гугл таблицы
    data = wks.get_all_values()

    # подключаемся к базе, используя реальные имя базы. пользователя и пароль
    conn = psycopg2.connect(dbname='db_name', user='postgres', password='password', host='localhost')
    cursor = conn.cursor()

    # удаление данных из таблицы в постгре
    cursor.execute("""DELETE FROM "Kurs" """)
    conn.commit()

    ## чтение из файла и заполнение словаря с курсами валют 
    kurs_d={}
    # если файла нет, заполняем его по новой, на те даты, что есть в файле гугл таблицы
    if not os.path.exists('k.txt'):  
        kurs_d={}
        for i in data:
            if i==data[0]:
                pass
            else:
                d=i[3].replace('.','/')
                kurs_d[d]=dobavlenie_kursa(get_root(d)) 
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
        if i==data[0]:
            pass
        else:
            d=i[3]
            d=d.replace('.','/')
            if d not in kurs_d: # если в текстовом файле нет нужного курса, он берется с сайта ЦБРФ
                kurs_d[d]=dobavlenie_kursa(get_root(d))
            k=kurs_d[d]
            k=k.replace(',','.')
            rub=float(k)*int(i[2])
            i.append(round(rub,2))

    # заполняем таблицу POstgreSQL данными из списка data
    for row in data[1:]:
        cursor.execute("""INSERT INTO "Kurs" (№, "Number", "Price_doll", "Date", "Price_rub")
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
    d= tomorrow.strftime("%d/%m/%Y")
    now = datetime.datetime.now()
    if now.hour == 16:
        kurs_d[d]=dobavlenie_kursa(get_root(d))
        with open('k.txt', 'w') as f:
            for key, value in kurs_d.items():
                f.write(key + ' ' + value + '\n')


# отсчет времени для двух функций
while True:
    t30 += 1
    t3600 += 1
    # каждые 30 секунд происходит подключение к гугл таблице, перерасчет рублевой стоимости, 
    # а также перенос данных в базу PostgreSQL
    if t30>30: 
        kurs_d= main()
        t30 = 0
    # каждый час происходит проверка времени. Когда наступает 16 часов, 
    # курс валюты за завтрашний день вносится к текстовый файл k.txt
    if t3600>3600: 
        new_kurs_from_site(kurs_d)
        t3600 = 0
    time.sleep(1)
