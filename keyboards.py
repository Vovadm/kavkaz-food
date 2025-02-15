from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_recipe_keyboard(recipes, page):
    buttons = [
        InlineKeyboardButton(
            text=recipe.title, callback_data=f"recipe_{recipe.id}"
        )
        for recipe in recipes
    ]
    grouped_buttons = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]

    keyboard = InlineKeyboardMarkup(inline_keyboard=grouped_buttons)

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="Назад", callback_data=f"page_{page - 1}"
            )
        )
    navigation_buttons.append(
        InlineKeyboardButton(text="Вперед", callback_data=f"page_{page + 1}")
    )

    if navigation_buttons:
        keyboard.inline_keyboard.append(navigation_buttons)

    return keyboard
