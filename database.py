# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class TodayStats:
    total: int
    by_category: dict[str, int]


@dataclass(frozen=True)
class WeekStats:
    total: int
    by_day: list[tuple[str, int]]  # [(YYYY-MM-DD, sum), ...]


@dataclass(frozen=True)
class SearchResult:
    items: list[tuple[str, str, int, str | None]]  # [(date, category, amount, comment), ...]
    total: int


def _date_from_iso(value: str) -> date:
    return date.fromisoformat(value)


def _iso_from_date(value: date) -> str:
    return value.isoformat()


def _add_months(d: date, months: int) -> date:
    """
    Добавляет месяцы к дате.
    Если целевой месяц короче текущего, ставим последний день месяца.
    """
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def _add_years(d: date, years: int) -> date:
    try:
        return date(d.year + years, d.month, d.day)
    except ValueError:
        # например, 29 февраля
        return date(d.year + years, d.month, 28)


class Database:
    def __init__(self, db_path: str = "expenses.sqlite3") -> None:
        self.db_path = db_path
        # check_same_thread=False нужен, чтобы безопаснее запускать в async-проекте.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_db(self) -> None:
        try:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    comment TEXT,
                    date TEXT NOT NULL DEFAULT (DATE('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_expenses_user_date
                    ON expenses(user_id, date);

                CREATE INDEX IF NOT EXISTS idx_expenses_user_category_date
                    ON expenses(user_id, category, date);

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'RUB',
                    google_spreadsheet_id TEXT,
                    registered_at TEXT NOT NULL DEFAULT (DATE('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_users_is_banned
                    ON users(is_banned);

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reminder_type TEXT NOT NULL,
                    next_date TEXT NOT NULL,           -- YYYY-MM-DD
                    amount INTEGER NOT NULL,          -- примерная сумма
                    periodicity TEXT NOT NULL,        -- once/monthly/yearly
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (DATE('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_reminders_user_active
                    ON reminders(user_id, is_active);

                CREATE INDEX IF NOT EXISTS idx_reminders_next_date
                    ON reminders(next_date, is_active);
                """
            )
            print("[database] init_db: schema ensured")
        except Exception as e:
            print(f"[database] init_db error: {e}")
            raise

    def add_expense(
        self,
        user_id: int,
        amount: int,
        category: str,
        comment: str | None,
    ) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO expenses(user_id, amount, category, comment)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, amount, category, comment),
                )
        except Exception as e:
            print(f"[database] add_expense error: {e}")
            raise

    def get_today_stats(self, user_id: int) -> TodayStats:
        try:
            total_row = self.conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM expenses
                WHERE user_id = ? AND date = DATE('now')
                """,
                (user_id,),
            ).fetchone()

            total = int(total_row["total"] or 0)

            rows = self.conn.execute(
                """
                SELECT category, COALESCE(SUM(amount), 0) AS total
                FROM expenses
                WHERE user_id = ? AND date = DATE('now')
                GROUP BY category
                ORDER BY category
                """,
                (user_id,),
            ).fetchall()

            by_category: dict[str, int] = {}
            for r in rows:
                by_category[str(r["category"])] = int(r["total"] or 0)

            return TodayStats(total=total, by_category=by_category)
        except Exception as e:
            print(f"[database] get_today_stats error: {e}")
            raise

    def get_week_stats(self, user_id: int) -> WeekStats:
        """
        Берем текущие сутки как DATE('now') в SQLite и последние 6 дней до них.
        """
        try:
            total_row = self.conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM expenses
                WHERE user_id = ?
                  AND date BETWEEN DATE('now', '-6 day') AND DATE('now')
                """,
                (user_id,),
            ).fetchone()
            total = int(total_row["total"] or 0)

            rows = self.conn.execute(
                """
                SELECT date, COALESCE(SUM(amount), 0) AS total
                FROM expenses
                WHERE user_id = ?
                  AND date BETWEEN DATE('now', '-6 day') AND DATE('now')
                GROUP BY date
                ORDER BY date
                """,
                (user_id,),
            ).fetchall()

            by_day: list[tuple[str, int]] = [(str(r["date"]), int(r["total"] or 0)) for r in rows]
            return WeekStats(total=total, by_day=by_day)
        except Exception as e:
            print(f"[database] get_week_stats error: {e}")
            raise

    # -----------------------------
    # Users / ban / currency (PROMPT #8 / #3)
    # -----------------------------

    def upsert_user(self, user_id: int, username: str | None) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO users(user_id, username)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username
                    """,
                    (user_id, username),
                )
        except Exception as e:
            print(f"[database] upsert_user error: {e}")
            raise

    def is_user_banned(self, user_id: int) -> bool:
        try:
            row = self.conn.execute(
                "SELECT is_banned FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return False
            return int(row["is_banned"]) == 1
        except Exception as e:
            print(f"[database] is_user_banned error: {e}")
            raise

    def set_ban(self, user_id: int, is_banned: bool) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO users(user_id, is_banned)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        is_banned = excluded.is_banned
                    """,
                    (user_id, 1 if is_banned else 0),
                )
        except Exception as e:
            print(f"[database] set_ban error: {e}")
            raise

    def get_user_currency(self, user_id: int) -> str:
        try:
            row = self.conn.execute(
                "SELECT currency FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return "RUB"
            return str(row["currency"] or "RUB")
        except Exception as e:
            print(f"[database] get_user_currency error: {e}")
            raise

    def set_user_currency(self, user_id: int, currency: str) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE users SET currency = ? WHERE user_id = ?",
                    (currency, user_id),
                )
        except Exception as e:
            print(f"[database] set_user_currency error: {e}")
            raise

    def get_user_google_spreadsheet_id(self, user_id: int) -> str | None:
        try:
            row = self.conn.execute(
                "SELECT google_spreadsheet_id FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return row["google_spreadsheet_id"]
        except Exception as e:
            print(f"[database] get_user_google_spreadsheet_id error: {e}")
            raise

    def set_user_google_spreadsheet_id(self, user_id: int, spreadsheet_id: str) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE users SET google_spreadsheet_id = ? WHERE user_id = ?",
                    (spreadsheet_id, user_id),
                )
        except Exception as e:
            print(f"[database] set_user_google_spreadsheet_id error: {e}")
            raise

    # -----------------------------
    # Profile stats (PROMPT #3)
    # -----------------------------

    def get_total_stats(self, user_id: int) -> int:
        try:
            row = self.conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM expenses
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return int(row["total"] or 0)
        except Exception as e:
            print(f"[database] get_total_stats error: {e}")
            raise

    def get_expenses_count(self, user_id: int) -> int:
        try:
            row = self.conn.execute(
                "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return int(row["cnt"] or 0)
        except Exception as e:
            print(f"[database] get_expenses_count error: {e}")
            raise

    def get_most_frequent_category(self, user_id: int) -> str | None:
        try:
            row = self.conn.execute(
                """
                SELECT category, COUNT(*) AS c
                FROM expenses
                WHERE user_id = ?
                GROUP BY category
                ORDER BY c DESC, category ASC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return str(row["category"])
        except Exception as e:
            print(f"[database] get_most_frequent_category error: {e}")
            raise

    def get_expenses_for_export(self, user_id: int) -> list[sqlite3.Row]:
        try:
            rows = self.conn.execute(
                """
                SELECT id, user_id, amount, category, comment, date
                FROM expenses
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
            return rows
        except Exception as e:
            print(f"[database] get_expenses_for_export error: {e}")
            raise

    def get_expenses_for_export_all(self) -> list[sqlite3.Row]:
        try:
            rows = self.conn.execute(
                """
                SELECT id, user_id, amount, category, comment, date
                FROM expenses
                ORDER BY date ASC, id ASC
                """,
            ).fetchall()
            return rows
        except Exception as e:
            print(f"[database] get_expenses_for_export_all error: {e}")
            raise

    def get_all_user_ids(self) -> list[int]:
        try:
            rows = self.conn.execute(
                "SELECT user_id FROM users ORDER BY user_id ASC"
            ).fetchall()
            return [int(r["user_id"]) for r in rows]
        except Exception as e:
            print(f"[database] get_all_user_ids error: {e}")
            raise

    # -----------------------------
    # Graph / search helpers
    # -----------------------------

    def get_expenses_by_category_between(
        self,
        user_id: int,
        start_date: str | None,
        end_date: str | None,
    ) -> dict[str, int]:
        try:
            sql = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ?"
            params: list[Any] = [user_id]
            if start_date and end_date:
                sql += " AND date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                sql += " AND date >= ?"
                params.append(start_date)
            elif end_date:
                sql += " AND date <= ?"
                params.append(end_date)
            sql += " GROUP BY category"
            rows = self.conn.execute(sql, tuple(params)).fetchall()
            return {str(r["category"]): int(r["total"] or 0) for r in rows}
        except Exception as e:
            print(f"[database] get_expenses_by_category_between error: {e}")
            raise

    def get_expenses_by_day_between(self, user_id: int, start_date: str, end_date: str) -> list[tuple[str, int]]:
        try:
            rows = self.conn.execute(
                """
                SELECT date, SUM(amount) AS total
                FROM expenses
                WHERE user_id = ?
                  AND date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date ASC
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [(str(r["date"]), int(r["total"] or 0)) for r in rows]
        except Exception as e:
            print(f"[database] get_expenses_by_day_between error: {e}")
            raise

    def search_expenses(
        self,
        user_id: int,
        start_date: str | None,
        end_date: str | None,
        category: str | None,
        amount_min: int | None,
        amount_max: int | None,
        comment_contains: str | None,
        limit: int,
        offset: int,
    ) -> SearchResult:
        try:
            where = ["user_id = ?"]
            params: list[Any] = [user_id]

            if start_date:
                where.append("date >= ?")
                params.append(start_date)
            if end_date:
                where.append("date <= ?")
                params.append(end_date)
            if category:
                where.append("category = ?")
                params.append(category)
            if amount_min is not None:
                where.append("amount >= ?")
                params.append(amount_min)
            if amount_max is not None:
                where.append("amount <= ?")
                params.append(amount_max)
            if comment_contains:
                where.append("COALESCE(comment, '') LIKE ?")
                params.append(f"%{comment_contains}%")

            where_sql = " AND ".join(where)

            count_row = self.conn.execute(
                f"SELECT COUNT(*) AS total FROM expenses WHERE {where_sql}",
                tuple(params),
            ).fetchone()
            total = int(count_row["total"] or 0)

            rows = self.conn.execute(
                f"""
                SELECT date, category, amount, comment
                FROM expenses
                WHERE {where_sql}
                ORDER BY date DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params + [limit, offset]),
            ).fetchall()

            items: list[tuple[str, str, int, str | None]] = []
            for r in rows:
                items.append((str(r["date"]), str(r["category"]), int(r["amount"]), r["comment"]))
            return SearchResult(items=items, total=total)
        except Exception as e:
            print(f"[database] search_expenses error: {e}")
            raise

    # -----------------------------
    # Reminders (PROMPT #7)
    # -----------------------------

    def add_reminder(
        self,
        user_id: int,
        reminder_type: str,
        next_date: str,
        amount: int,
        periodicity: str,
    ) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO reminders(user_id, reminder_type, next_date, amount, periodicity)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, reminder_type, next_date, amount, periodicity),
                )
        except Exception as e:
            print(f"[database] add_reminder error: {e}")
            raise

    def get_active_reminders(self, user_id: int) -> list[sqlite3.Row]:
        try:
            rows = self.conn.execute(
                """
                SELECT id, reminder_type, next_date, amount, periodicity
                FROM reminders
                WHERE user_id = ? AND is_active = 1
                ORDER BY next_date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
            return rows
        except Exception as e:
            print(f"[database] get_active_reminders error: {e}")
            raise

    def get_due_reminders(self, from_date: str, to_date: str) -> list[sqlite3.Row]:
        try:
            rows = self.conn.execute(
                """
                SELECT id, user_id, reminder_type, next_date, amount, periodicity
                FROM reminders
                WHERE is_active = 1
                  AND next_date BETWEEN ? AND ?
                ORDER BY next_date ASC, id ASC
                """,
                (from_date, to_date),
            ).fetchall()
            return rows
        except Exception as e:
            print(f"[database] get_due_reminders error: {e}")
            raise

    def mark_reminder_after_sent(self, reminder_id: int, periodicity: str) -> None:
        try:
            with self.conn:
                if periodicity == "once":
                    self.conn.execute(
                        "UPDATE reminders SET is_active = 0 WHERE id = ?",
                        (reminder_id,),
                    )
                    return

                row = self.conn.execute(
                    "SELECT next_date FROM reminders WHERE id = ?",
                    (reminder_id,),
                ).fetchone()
                if not row:
                    return

                cur = _date_from_iso(str(row["next_date"]))
                if periodicity == "monthly":
                    nxt = _add_months(cur, 1)
                elif periodicity == "yearly":
                    nxt = _add_years(cur, 1)
                else:
                    nxt = cur + timedelta(days=30)

                self.conn.execute(
                    "UPDATE reminders SET next_date = ? WHERE id = ?",
                    (_iso_from_date(nxt), reminder_id),
                )
        except Exception as e:
            print(f"[database] mark_reminder_after_sent error: {e}")
            raise

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception as e:
            print(f"[database] close error: {e}")


class FuelDatabase:
    def __init__(self, db_path: str = "expenses.sqlite3") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_db(self) -> None:
        try:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS fuel_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    liters REAL NOT NULL,
                    price_per_liter REAL NOT NULL,
                    total_cost INTEGER NOT NULL,
                    mileage REAL NOT NULL,
                    date TEXT NOT NULL DEFAULT (DATE('now')),
                    car_model TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_fuel_user_date
                    ON fuel_logs(user_id, date);

                CREATE INDEX IF NOT EXISTS idx_fuel_user_mileage
                    ON fuel_logs(user_id, mileage);
                """
            )
            print("[fuel_database] init_db: schema ensured")
        except Exception as e:
            print(f"[fuel_database] init_db error: {e}")
            raise

    def get_last_mileage(self, user_id: int) -> float | None:
        row = self.conn.execute(
            """
            SELECT mileage
            FROM fuel_logs
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return float(row["mileage"])

    def add_fuel_log(
        self,
        user_id: int,
        liters: float,
        price_per_liter: float,
        mileage: float,
        car_model: str,
    ) -> None:
        try:
            last = self.get_last_mileage(user_id)
            if last is not None and mileage <= last:
                raise ValueError(
                    f"Пробег меньше/равен предыдущему. Предыдущий: {last:g}, текущий: {mileage:g}"
                )

            total_cost = int(round(liters * price_per_liter))
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO fuel_logs(user_id, liters, price_per_liter, total_cost, mileage, car_model)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, liters, price_per_liter, total_cost, mileage, car_model),
                )
        except Exception as e:
            print(f"[fuel_database] add_fuel_log error: {e}")
            raise

    def _get_logs_with_consumption(self, user_id: int) -> list[tuple[int, str, float, float, int]]:
        """
        Возвращает список: (fuel_log_id, date, mileage, consumption_l_per_100km, total_cost)
        consumption считается относительно предыдущей заправки.
        """
        rows = self.conn.execute(
            """
            SELECT id, date, mileage, liters, total_cost
            FROM fuel_logs
            WHERE user_id = ?
            ORDER BY date ASC, id ASC
            """,
            (user_id,),
        ).fetchall()

        points: list[tuple[int, str, float, float, int]] = []
        prev_mileage: float | None = None
        for r in rows:
            log_id = int(r["id"])
            dt = str(r["date"])
            mile = float(r["mileage"])
            liters = float(r["liters"])
            total_cost = int(r["total_cost"])

            if prev_mileage is None:
                prev_mileage = mile
                continue

            distance = mile - prev_mileage
            if distance <= 0:
                prev_mileage = mile
                continue

            consumption = (liters / distance) * 100.0
            points.append((log_id, dt, mile, consumption, total_cost))
            prev_mileage = mile

        return points

    def get_fuel_stats(self, user_id: int) -> dict[str, int | float | None]:
        try:
            points = self._get_logs_with_consumption(user_id)
            total_cost_row = self.conn.execute(
                "SELECT COALESCE(SUM(total_cost), 0) AS total FROM fuel_logs WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            total_cost = int(total_cost_row["total"] or 0)

            if not points:
                return {
                    "avg_last_5": None,
                    "min_consumption": None,
                    "max_consumption": None,
                    "total_cost": total_cost,
                }

            last_5 = points[-5:]
            avg_last_5 = sum(p[3] for p in last_5) / len(last_5)
            min_consumption = min(p[3] for p in points)
            max_consumption = max(p[3] for p in points)

            return {
                "avg_last_5": avg_last_5,
                "min_consumption": min_consumption,
                "max_consumption": max_consumption,
                "total_cost": total_cost,
            }
        except Exception as e:
            print(f"[fuel_database] get_fuel_stats error: {e}")
            raise

    def get_fuel_points_for_graph(self, user_id: int) -> list[tuple[float, float]]:
        points = self._get_logs_with_consumption(user_id)
        return [(p[2], p[3]) for p in points]

    def get_fuel_logs_for_export(self, user_id: int) -> list[sqlite3.Row]:
        try:
            rows = self.conn.execute(
                """
                SELECT id, user_id, liters, price_per_liter, total_cost, mileage, date, car_model
                FROM fuel_logs
                WHERE user_id = ?
                ORDER BY date ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
            return rows
        except Exception as e:
            print(f"[fuel_database] get_fuel_logs_for_export error: {e}")
            raise

    def get_fuel_logs_for_export_all(self) -> list[sqlite3.Row]:
        try:
            rows = self.conn.execute(
                """
                SELECT id, user_id, liters, price_per_liter, total_cost, mileage, date, car_model
                FROM fuel_logs
                ORDER BY date ASC, id ASC
                """
            ).fetchall()
            return rows
        except Exception as e:
            print(f"[fuel_database] get_fuel_logs_for_export_all error: {e}")
            raise

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception as e:
            print(f"[fuel_database] close error: {e}")


