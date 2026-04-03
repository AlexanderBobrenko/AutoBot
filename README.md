# Car Cost Bot

Telegram-бот для учёта расходов и заправок автомобиля (с графиками и экспортом в Excel).

## Что делает бот

- Записывает расходы по категориям (с комментарием) и показывает статистику за `сегодня` и `7 дней`.
- Записывает заправки (литры, цена/литр, пробег) и показывает статистику по топливу.
- Строит графики расходов и расхода топлива.
- Экспортирует данные в `xlsx`.
- Поддерживает напоминания.
- Опционально может синхронизироваться с Google Sheets через команду `/connect_google`.

## Безопасность (важно)

Не коммитьте в репозиторий секреты и данные:

- `TOKEN` храните в переменных окружения (или локально в `.env`).
- `credentials.json` (ключ для Google) добавлен в `.gitignore`.
- `expenses.sqlite3` добавлен в `.gitignore` (БД не должна попадать в GitHub).

Для примера переменных используйте файл `.env.example`.

## Локальный запуск

1. Установите Python 3.10+.
2. Создайте виртуальное окружение:

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

4. Создайте `.env` из шаблона:

   ```bash
   copy .env.example .env   # Windows
   cp .env.example .env    # Linux/macOS
   ```

   И укажите `TOKEN` (обязательно).

5. Запустите бота:

   ```bash
   python bot.py
   ```

## Переменные окружения

Бот использует:

- `TOKEN` (обязательно) — токен Telegram-бота.
- `ADMIN_IDS` (опционально) — список admin user_id через запятую, например `123,456`.
- `USD_RUB_RATE` (опционально) — курс RUB за 1 USD (по умолчанию `90.0`).
- `EUR_RUB_RATE` (опционально) — курс RUB за 1 EUR (по умолчанию `100.0`).

## Деплой на Railway.app (бесплатный)

1. Создайте проект на Railway и подключите репозиторий GitHub.
2. В Railway добавьте переменные окружения:
   - `TOKEN`
   - `ADMIN_IDS`
   - `USD_RUB_RATE`
   - `EUR_RUB_RATE`
3. В репозитории уже есть `Procfile`. Команда запуска:

   - `worker: python bot.py`

### Важно про `expenses.sqlite3`

Бот хранит данные в файле `expenses.sqlite3` в рабочей директории.

На Railway без постоянного хранилища файл может быть утерян при пересборке/перезапуске. Если вам важна сохранность данных, включайте доступное в вашем тарифе постоянное хранилище (volume) и монтируйте его так, чтобы `expenses.sqlite3` оставался на диске.

### Google Sheets (`credentials.json`)

Команда `/connect_google` ожидает файл `credentials.json` в корне проекта рядом с `bot.py`.

На Railway файл нужно предоставить в окружении деплоя (не коммить в GitHub). Если у вас нет способа передать файл, не используйте `/connect_google`.

## Деплой на бесплатный VPS (Oracle Cloud Always Free)

Ниже пример для Ubuntu/Debian-подобной системы.

1. Зайдите на VPS по SSH.
2. Установите Python и зависимости системы (особенно для `matplotlib` может понадобиться):

   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv python3-pip
   sudo apt-get install -y build-essential
   ```

3. Создайте папку проекта и пользователя (пример):

   ```bash
   sudo useradd -r -m -s /bin/bash car_cost_bot || true
   sudo mkdir -p /opt/car_cost_bot
   sudo chown -R car_cost_bot:car_cost_bot /opt/car_cost_bot
   ```

4. Склонируйте репозиторий:

   ```bash
   cd /opt/car_cost_bot
   sudo -u car_cost_bot git clone https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO>.git .
   ```

5. Создайте `.env`:

   ```bash
   sudo -u car_cost_bot cp .env.example .env
   sudo -u car_cost_bot nano .env
   ```

6. Виртуальное окружение и зависимости:

   ```bash
   cd /opt/car_cost_bot
   sudo -u car_cost_bot python3 -m venv venv
   sudo -u car_cost_bot ./venv/bin/pip install -r requirements.txt
   ```

7. Установите systemd unit:

   ```bash
   sudo cp /opt/car_cost_bot/car-cost-bot.service /etc/systemd/system/car-cost-bot.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now car-cost-bot
   ```

8. Проверка и логи:

   ```bash
   sudo systemctl status car-cost-bot --no-pager
   sudo journalctl -u car-cost-bot -f
   ```

## Telegram команды

### Пользовательские команды

- `/start`
- `/currency`
- `/search` — открывает меню поиска (дальше используются кнопки)
- `/connect_google` — синхронизация с Google Sheets (нужен `credentials.json`)

Кнопки главного меню:

- `➕ Добавить расход`
- `📊 Статистика за сегодня`
- `📈 Статистика за неделю`
- `👤 Мой профиль`
- `⛽ Заправка`
- `📊 Расход топлива`
- `📊 График расходов`
- `📉 Динамика`
- `⛽ График расхода`
- `⏰ Напоминания`
- `📋 Список напоминаний`
- `📎 Экспорт в Excel`

### Админские команды

Эти команды доступны только admin’ам из `ADMIN_IDS`:

- `/users`
- `/ban <user_id>`
- `/unban <user_id>`
- `/broadcast <text>`
- `/stats_all`
- `/top_users`
- `/export_all`

## Troubleshooting

- Если видите ошибку `TOKEN не задан`, проверьте `TOKEN` в переменных окружения (Railway/VPS) или локально в `.env`.
- Если возникают проблемы со сборкой `matplotlib`, чаще всего нужны системные библиотеки/компилятор (зависит от окружения). Сообщите текст ошибки — подскажу точный набор пакетов.

