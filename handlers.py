import re

from aiogram import Dispatcher, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from keyboards import get_recipe_keyboard
from parsing import AsyncSessionLocal, Recipe


class Form(StatesGroup):
    waiting_for_portions = State()


router = Router()


@router.message(F.text == "/start")
async def send_welcome(message: types.Message):
    await message.answer(
        "Привет! Нажмите кнопку, чтобы просмотреть рецепты.",
        reply_markup=get_recipe_keyboard([], 0),
    )


@router.callback_query(F.data.startswith("page_"))
async def handle_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1]) - 1
    async with AsyncSessionLocal() as session:

        query = select(Recipe).offset(page * 5).limit(5)
        recipes = await session.execute(query)

        recipes = recipes.scalars().all()

        await callback.message.edit_text(
            "Вот наши рецепты:",
            reply_markup=get_recipe_keyboard(recipes, page),
        )


@router.callback_query(F.data.startswith("recipe_"))
async def handle_recipe(callback: types.CallbackQuery, state: FSMContext):
    recipe_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:

        recipe = await session.get(Recipe, recipe_id)
        if recipe:

            await callback.message.answer(
                "Сколько порций вы хотите приготовить?"
            )
            await state.update_data(recipe_id=recipe_id)
            await state.set_state(Form.waiting_for_portions)
            await callback.answer()
        else:
            await callback.answer("Рецепт не найден.")


@router.message(Form.waiting_for_portions)
async def handle_portions(message: types.Message, state: FSMContext):

    input_text = message.text.strip()

    input_text = input_text.replace(",", ".")

    try:
        portions = float(input_text)
        print(f"Received portions: {portions}")
    except ValueError:
        message_text = (
            "Пожалуйста, введите целое число "
            "или число с плавающей запятой для количества порций."
        )
        await message.answer(message_text)
        return

    data = await state.get_data()
    recipe_id = data.get("recipe_id")

    async with AsyncSessionLocal() as session:

        recipe = await session.get(Recipe, recipe_id)
        if recipe:

            about = recipe.about
            ingredients = recipe.ingredients
            instruction = recipe.instructions
            image = recipe.image_url
            proteins = recipe.proteins
            fats = recipe.fats
            carbs = recipe.carbs
            calories = recipe.calories

            def multiply_by_portions(match):

                number = float(match.group().replace(",", "."))
                result = round(number * portions, 2)
                print(f"Multiplying {number} by {portions} to get {result}")
                return str(result)

            modified_ingredients = re.sub(
                r"(\d+([.,]\d+)?)", multiply_by_portions, ingredients.strip()
            )

            await message.answer_photo(image)
            await message.answer(about)

            await message.answer(
                f"Для {portions} порций вам понадобятся:\n"
                f"{modified_ingredients}"
            )

            async def send_long_message(message, text):
                chunk_size = 4096
                for i in range(0, len(text), chunk_size):
                    await message.answer(text[i : i + chunk_size])

            await send_long_message(message, instruction)

            await message.answer(
                "КБЖУ на 100г\n"
                f"Калории: {calories}\n"
                f"Белки: {proteins}\n"
                f"Жиры: {fats}\n"
                f"Углеводы: {carbs}"
            )

            await message.answer(
                "Хотите еще рецепты? Используйте кнопку ниже!",
                reply_markup=get_recipe_keyboard([], 0),
            )

        else:
            await message.answer("Рецепт не найден.")


@router.callback_query(F.data == "search_more")
async def handle_search_more(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:

        recipes = await session.execute(select(Recipe).limit(5))
        recipes = recipes.scalars().all()

        await callback.message.edit_text(
            "Вот доступные рецепты:",
            reply_markup=get_recipe_keyboard(recipes, 0),
        )
        await callback.answer()


def register_handlers(dp: Dispatcher):
    dp.include_router(router)
