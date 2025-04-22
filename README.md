# Телеграм-бот по Кавказской кухне

Мой проект предладлагает рецепты Казвказской кухни прямо в телеграме

## 🚀 Возможности

- 📃 Функциональное меню с выбором блюд

- 🍇 Расчет количесто ингридиентов, для опредленного числа порций

- 📄 Краткое описание о каждом блюде

- 🟰 Отображение КБЖУ для каждого варианта


## 📦 Установка
1. Клонируй репозиторий:
```bash
git clone https://github.com/Vovadm/kavkaz-food.git
cd behavior
```

2. Создай и активируй виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Для Linux/macOS
venv\Scripts\activate     # Для Windows
```

3. Установи зависимости
```bash
pip install -r requirements.txt
```

4. Создай .env файл и добавь в него:
```bash
DB_URL = mariadb+aiomysql://{USER}:{PASS}@{HOST:PORT}/{DB_NAME}
TOKEN = TOKEN-HERE
```


## 🏃 Запуск
```bash
python main.py
```


## 💻 Программный-код

- [`main.py`](/main.py) - файл запуска бота

- [`handlers.py`](/handlers.py) - обработчик событий 

- [`parsing.py`](/parsing.py) - парсинг данных сайта

- [`keyboards.py`](/keyboards.py) - создание клавиатур



