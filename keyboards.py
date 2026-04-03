# -*- coding: utf-8 -*-
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


MAIN_BUTTON_ADD = "➕ Добавить расход"
MAIN_BUTTON_TODAY = "📊 Статистика за сегодня"
MAIN_BUTTON_WEEK = "📈 Статистика за неделю"
MAIN_BUTTON_PROFILE = "👤 Мой профиль"

MAIN_BUTTON_ADD_FUEL = "⛽ Заправка"
MAIN_BUTTON_FUEL_STATS = "📊 Расход топлива"

MAIN_BUTTON_GRAPH_EXPENSES = "📊 График расходов"
MAIN_BUTTON_DYNAMIC_EXPENSES = "📉 Динамика"
MAIN_BUTTON_GRAPH_FUEL = "⛽ График расхода"

MAIN_BUTTON_REMINDERS = "⏰ Напоминания"
MAIN_BUTTON_REMINDERS_LIST = "📋 Список напоминаний"

MAIN_BUTTON_EXPORT_EXCEL = "📎 Экспорт в Excel"


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MAIN_BUTTON_ADD), KeyboardButton(text=MAIN_BUTTON_ADD_FUEL)],
            [KeyboardButton(text=MAIN_BUTTON_TODAY), KeyboardButton(text=MAIN_BUTTON_FUEL_STATS)],
            [KeyboardButton(text=MAIN_BUTTON_WEEK), KeyboardButton(text=MAIN_BUTTON_PROFILE)],
            [KeyboardButton(text=MAIN_BUTTON_GRAPH_EXPENSES), KeyboardButton(text=MAIN_BUTTON_DYNAMIC_EXPENSES)],
            [KeyboardButton(text=MAIN_BUTTON_GRAPH_FUEL), KeyboardButton(text=MAIN_BUTTON_REMINDERS)],
            [KeyboardButton(text=MAIN_BUTTON_REMINDERS_LIST), KeyboardButton(text=MAIN_BUTTON_EXPORT_EXCEL)],
        ],
        resize_keyboard=True,
    )


def get_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for idx, category in enumerate(categories, start=1):
        row.append(
            InlineKeyboardButton(
                text=category,
                callback_data=f"cat:{category}",
            )
        )
        if idx % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_currency_keyboard(currencies: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{c}", callback_data=f"currency:{c}")
                for c in currencies
            ]
        ]
    )


def get_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Неделя", callback_data="period:week")],
            [InlineKeyboardButton(text="Месяц", callback_data="period:month")],
            [InlineKeyboardButton(text="Всё время", callback_data="period:all")],
        ]
    )


def get_reminder_types_keyboard() -> InlineKeyboardMarkup:
    types = ["ТО", "Страховка", "Налог", "Шиномонтаж", "Другое"]
    buttons: list[list[InlineKeyboardButton]] = []
    for i, t in enumerate(types):
        buttons.append([InlineKeyboardButton(text=t, callback_data=f"rem_type:{t}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_periodicity_keyboard() -> InlineKeyboardMarkup:
    items = [("разово", "once"), ("ежемесячно", "monthly"), ("ежегодно", "yearly")]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"rem_period:{value}")] for label, value in items
        ]
    )


def get_search_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 За сегодня", callback_data="search:date_today")],
            [InlineKeyboardButton(text="📅 Вчера", callback_data="search:date_yesterday")],
            [InlineKeyboardButton(text="📅 Эта неделя", callback_data="search:date_week")],
            [InlineKeyboardButton(text="📅 Этот месяц", callback_data="search:date_month")],
            [InlineKeyboardButton(text="📅 Диапазон дат", callback_data="search:date_range")],
            [InlineKeyboardButton(text="⛽ Категория", callback_data="search:category")],
            [InlineKeyboardButton(text="💰 Больше чем X", callback_data="search:amount_gt")],
            [InlineKeyboardButton(text="💰 Меньше чем X", callback_data="search:amount_lt")],
            [InlineKeyboardButton(text="💰 В диапазоне X-Y", callback_data="search:amount_between")],
            [InlineKeyboardButton(text="📝 Комментарий", callback_data="search:comment")],
            [InlineKeyboardButton(text="🧩 Комбинированный поиск", callback_data="search:combined")],
        ]
    )


def get_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    # Кнопки "Вперед/Назад" согласно PROMPT #9.
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    if page > 1:
        row.append(InlineKeyboardButton(text="Назад", callback_data=f"search_page:{page-1}"))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="Вперед", callback_data=f"search_page:{page+1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

