import asyncio
import os
import re
import time

from dotenv import load_dotenv
from g4f.client import AsyncClient
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from webdriver_manager.chrome import ChromeDriverManager



load_dotenv()
DATABASE_URL = os.getenv("DB_URL")


engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()


# Модель для рецепта
class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    image_url = Column(String(255))
    ingredients = Column(Text, nullable=False)
    proteins = Column(Float)
    fats = Column(Float)
    carbs = Column(Float)
    calories = Column(Float)
    instructions = Column(Text, nullable=False)
    about = Column(Text)  # Новый столбец для краткого описания блюда


# Инициализация базы данных с удалением старых таблиц
async def init_db():
    # Удаление старой таблицы (если существует)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Создание новой таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Настройка драйвера Selenium для работы с браузером
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-webgl")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Список URL рецептов для парсинга
urls = [
    "https://1000.menu/cooking/44629-lezginskii-xinkal-tonkii",
    "https://1000.menu/cooking/20302-darginskii-xinkal",
    "https://1000.menu/cooking/15737-dagestanskii-avarskii-xinkal",
    "https://1000.menu/cooking/21429-chudu-s-zelenu",
    "https://1000.menu/cooking/24995-darginskoe-chudu-s-kartoshkoi",
    "https://1000.menu/cooking/17469-darginskii-chudu-s-мясом-картoшкoй",
    "https://1000.menu/cooking/20911-xychiny-s-kartoshkoi-i-syrom",
]


# Создаем экземпляр асинхронного клиента для общения с нейросетью
async def get_about_description(title):
    try:
        client = AsyncClient()  # Создаем экземпляр клиента
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Модель для генерации ответа
            messages=[
                {
                    "role": "user",
                    "content": f"Расскажи об этом блюде, что это такое, краткое описание: {title}",
                }
            ],
            web_search=False,
        )
        about = response.choices[0].message.content
        return about
    except Exception as e:
        print(f"Ошибка при получении описания: {e}")
        return "Описание не найдено"


# Функция для парсинга данных рецепта с сайта
async def parse_recipe(url):
    driver.get(url)
    time.sleep(2)

    try:
        yield_input = driver.find_element(By.ID, "yield_num_input")
        servings_count = int(yield_input.get_attribute("value"))
    except Exception:
        servings_count = 1

    try:
        title = driver.find_element(
            By.CSS_SELECTOR, 'h1[itemprop="name"]'
        ).text
    except Exception:
        title = "Не найдено"

    ingredients = []
    try:
        ingredient_elements = driver.find_elements(
            By.CSS_SELECTOR, ".ingredient"
        )
        for ingredient in ingredient_elements:
            ingredient_name = ingredient.find_element(
                By.CSS_SELECTOR, ".name"
            ).text
            ingredient_content = ingredient.find_element(
                By.CSS_SELECTOR, 'meta[itemprop="recipeIngredient"]'
            ).get_attribute("content")
            match = re.search(
                r"(\d+(\.\d+)?)\s?([а-яА-Я\.]+)", ingredient_content
            )

            if match:
                quantity = float(match.group(1))
                unit = match.group(3)
                quantity_per_serving = round(quantity / servings_count, 2)
                if quantity_per_serving == 0:
                    quantity_per_serving = "по вкусу"
                ingredients.append(
                    f"{ingredient_name} - {quantity_per_serving} {unit}"
                )
            else:
                ingredients.append(f"{ingredient_name} - по вкусу")
    except Exception:
        pass

    nutrition_values = {}
    try:
        nutrition_values["proteins"] = driver.find_element(
            By.ID, "nutr_p"
        ).text
        nutrition_values["fats"] = driver.find_element(By.ID, "nutr_f").text
        nutrition_values["carbs"] = driver.find_element(By.ID, "nutr_c").text
        nutrition_values["calories"] = driver.find_element(
            By.ID, "nutr_kcal"
        ).text
    except Exception:
        nutrition_values = {
            "proteins": 0,
            "fats": 0,
            "carbs": 0,
            "calories": 0,
        }

    instructions = "Инструкция не найдена"
    try:
        instructions = driver.find_element(
            By.CSS_SELECTOR, "div.instructions.fb-s"
        ).text
    except Exception:
        try:
            instructions = driver.find_element(
                By.CSS_SELECTOR, "ol.instructions"
            ).text
        except Exception:
            pass

    try:
        image_element = driver.find_element(
            By.CSS_SELECTOR, 'img[itemprop="image"]'
        )
        image_url = image_element.get_attribute("src")
        if image_url.startswith("//"):
            image_url = "https:" + image_url
    except Exception:
        image_url = "Не найдено"

    # Получаем описание блюда
    about = await get_about_description(title)

    return {
        "title": title,
        "servings_count": servings_count,
        "ingredients": "\n".join(ingredients),
        "nutrition_values": nutrition_values,
        "instructions": instructions,
        "image_url": image_url,
        "about": about,  # Добавляем описание
    }


# Функция для сохранения рецепта в базе данных
async def save_recipe(session: AsyncSession, recipe_data):
    async with session.begin():
        recipe = Recipe(
            title=recipe_data["title"],
            image_url=recipe_data["image_url"],
            ingredients=recipe_data["ingredients"],
            proteins=float(
                recipe_data["nutrition_values"].get("proteins") or 0
            ),
            fats=float(recipe_data["nutrition_values"].get("fats") or 0),
            carbs=float(recipe_data["nutrition_values"].get("carbs") or 0),
            calories=float(
                recipe_data["nutrition_values"].get("calories") or 0
            ),
            instructions=recipe_data["instructions"],
            about=recipe_data["about"],  # Сохраняем описание блюда
        )
        session.add(recipe)
    await session.commit()


# Основная асинхронная функция для запуска процесса
async def main():
    await init_db()
    recipes = []
    for url in urls:
        recipe = await parse_recipe(url)
        recipes.append(recipe)

        # Выводим информацию в консоль
        print(
            f"Название рецепта: {recipe['title']} (Количество порций: {recipe['servings_count']})"
        )
        print(f"Описание блюда: {recipe['about']}")
        print("Ингредиенты:")
        for ingredient in recipe["ingredients"].split("\n"):
            print(f"  {ingredient}")
        print(
            f"КБЖУ: Белки - {recipe['nutrition_values'].get('proteins')}, "
            f"Жиры - {recipe['nutrition_values'].get('fats')}, "
            f"Углеводы - {recipe['nutrition_values'].get('carbs')}, "
            f"Калории - {recipe['nutrition_values'].get('calories')}"
        )
        print("Инструкция по приготовлению:")
        print(recipe["instructions"])
        print(f"Ссылка на изображение: {recipe['image_url']}")
        print("-" * 40)

    # Сохранение рецептов в БД
    async with AsyncSessionLocal() as session:
        for recipe in recipes:
            await save_recipe(session, recipe)


# Запуск основного процесса
if __name__ == "__main__":
    asyncio.run(main())  # Запуск через новый цикл
    driver.quit()
