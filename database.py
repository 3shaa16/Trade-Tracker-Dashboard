import sqlite3
import pandas as pd

DB_NAME = "trades.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            starting_balance REAL NOT NULL,
            currency TEXT DEFAULT 'USD'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            entry_amount REAL NOT NULL,
            status TEXT NOT NULL,
            exit_amount REAL,
            profit_loss REAL,
            notes TEXT,
            link TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            closed_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_trade(
    date,
    title,
    entry_amount,
    status,
    exit_amount,
    profit_loss,
    notes,
    link
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trades
        (
            date,
            title,
            entry_amount,
            status,
            exit_amount,
            profit_loss,
            notes,
            link
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date,
        title,
        entry_amount,
        status,
        exit_amount,
        profit_loss,
        notes,
        link
    ))

    conn.commit()
    conn.close()

    export_trades_to_excel()


def get_all_trades():
    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM trades ORDER BY id DESC",
        conn
    )

    conn.close()

    return df


def export_trades_to_excel():
    df = get_all_trades()
    df.to_excel("trades.xlsx", index=False)


def get_dashboard_stats():
    df = get_all_trades()

    closed = df[df["status"] == "Closed"]

    total_profit = (
        closed["profit_loss"]
        .fillna(0)
        .sum()
    )

    total_closed = len(closed)

    total_open = len(
        df[df["status"] == "Open"]
    )

    wins = len(
        closed[
            closed["profit_loss"] > 0
        ]
    )

    win_rate = (
        (wins / total_closed) * 100
        if total_closed > 0
        else 0
    )

    return {
        "profit": total_profit,
        "closed": total_closed,
        "open": total_open,
        "win_rate": win_rate
    }


def close_trade(trade_id, exit_amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT entry_amount FROM trades WHERE id = ?",
        (trade_id,)
    )

    result = cursor.fetchone()

    if result:
        entry_amount = result[0]
        profit_loss = exit_amount - entry_amount

        cursor.execute("""
            UPDATE trades
            SET status = 'Closed',
                exit_amount = ?,
                profit_loss = ?,
                closed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (exit_amount, profit_loss, trade_id))

    conn.commit()
    conn.close()

    export_trades_to_excel()


def delete_trade(trade_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM trades WHERE id = ?",
        (trade_id,)
    )

    conn.commit()
    conn.close()

    export_trades_to_excel()


def save_profile(name, starting_balance, currency):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM profiles")

    cursor.execute("""
        INSERT INTO profiles (name, starting_balance, currency)
        VALUES (?, ?, ?)
    """, (name, starting_balance, currency))

    conn.commit()
    conn.close()


def get_profile():
    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM profiles LIMIT 1",
        conn
    )

    conn.close()

    if len(df) == 0:
        return None

    return df.iloc[0].to_dict()


def update_trade(
    trade_id,
    date,
    title,
    entry_amount,
    status,
    exit_amount,
    notes,
    link
):
    profit_loss = None

    if status == "Closed" and exit_amount is not None:
        profit_loss = exit_amount - entry_amount
    else:
        exit_amount = None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trades
        SET date = ?,
            title = ?,
            entry_amount = ?,
            status = ?,
            exit_amount = ?,
            profit_loss = ?,
            notes = ?,
            link = ?
        WHERE id = ?
    """, (
        date,
        title,
        entry_amount,
        status,
        exit_amount,
        profit_loss,
        notes,
        link,
        trade_id
    ))

    conn.commit()
    conn.close()

    export_trades_to_excel()