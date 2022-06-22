# From-Google_sheet_to_PostgreSQL

Скрипт корректирует и переносит данные между гугл таблицей и базой PostgreSQL.
Гугл таблица- https://docs.google.com/spreadsheets/d/1r3l-0EdTzpHnpDPX2_32fT69_RWx4IXiR9Xbi0D7Vh0/edit#gid=0
Срабатывает каждые 30 секунд для постоянного обновления базы.
Также каждый час происходит проверка времени. Если наступает 16 часов, то с сайта ЦБРФ считывается курс валюты на завтрашний день и записывается в текстовый файл "k.txt".

Работа скрипта:
1. Читает данные из гугл таблицы и переводит их в массив.
2. Проверяет, есть ли в файле "k.txt" нужный курс валюты на дату поставки в каждой строке. 
  2.1. Если да- по нему рассчитывает рублевую стоимость заказа и добавляется к каждой строчке массива.
  2.2. Если нет- считывает на указанную дату курс валюты с сайта ЦБРФ. Если на сайте еще нет курса на такую дату- подставляется курс за сегодня. 
  При наступлении даты поставки рублевая стоимость будет расчитана по актуальному курсу.
  2.3. Если файл "k.txt" отсутствует - он будет создан и заполнен курсами валют с сайта ЦБРФ на те даты, которые присутствуют в гугл таблице.
3. Происходит подключение к базе PostgreSQL, используя корректные имя пользователя, базы, а также пароль.
4. В базе очищается необходимая таблица. Очищение происходит каждый раз, чтобы сохранять целостность.
5. Массив с данными переносится в очищенную таблицу PostgreSQL.
6. Изменения сохраняются, происходит отключение от базы.

Все файлы необходимо располагать в одной папке. 
Папка состоит из файлов:
1. test_kurs.py - сам скрипт
2. "k.txt" - файл с курсами валюты.
3. test-kurs1-1aee0139edd0.json - файл, поддерживающий соединение к конкретной гугл таблице.

Скрипт запускается через терминал. Для постоянной фоновой работы его можно загрузить в Автозапуск/Службы и т.д. в зависимости от операционной системы.

