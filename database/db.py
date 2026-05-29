"""
db.py
-----
SQLite database manager for Etsy SEO Optimizer.
All scraping runs are stored here with run_date for trend tracking.

Usage:
    from database.db import EtsyDB
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime


DB_PATH = "data/etsy.db"


class EtsyDB:

    def __init__(self, db_path: str = DB_PATH):
        os.makedirs("data", exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
        print(f"[DB] Connected: {self.db_path}")

    def _create_tables(self):
        """Create tables if they don't exist yet."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id    TEXT,
                title         TEXT,
                price_usd     REAL,
                currency      TEXT,
                quantity      INTEGER,
                num_favorers  INTEGER,
                views         INTEGER,
                tags          TEXT,
                shop_id       TEXT,
                url           TEXT,
                state         TEXT,
                query         TEXT,
                run_date      TEXT,   -- YYYY-MM-DD of the scraping run
                scraped_at    TEXT    -- full UTC timestamp
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date    TEXT UNIQUE,
                total_rows  INTEGER,
                queries     TEXT,
                created_at  TEXT
            )
        """)

        self.conn.commit()

    def insert_listings(self, df: pd.DataFrame, run_date: str = None):
        """
        Insert a DataFrame of listings into the DB.
        run_date defaults to today (YYYY-MM-DD).
        """
        if run_date is None:
            run_date = datetime.utcnow().strftime("%Y-%m-%d")

        df = df.copy()
        df["run_date"] = run_date

        df.to_sql("listings", self.conn, if_exists="append", index=False)

        # Log this run
        queries = ", ".join(df["query"].unique().tolist())
        self.conn.execute("""
            INSERT OR REPLACE INTO runs (run_date, total_rows, queries, created_at)
            VALUES (?, ?, ?, ?)
        """, (run_date, len(df), queries, datetime.utcnow().isoformat()))
        self.conn.commit()

        print(f"[DB] Inserted {len(df)} rows for run_date={run_date}")

    def get_listings(self, run_date: str = None) -> pd.DataFrame:
        """
        Fetch listings from DB.
        If run_date given, return only that week's data.
        Otherwise return all.
        """
        if run_date:
            query = "SELECT * FROM listings WHERE run_date = ?"
            return pd.read_sql(query, self.conn, params=(run_date,))
        return pd.read_sql("SELECT * FROM listings", self.conn)

    def get_runs(self) -> pd.DataFrame:
        """Return all scraping run history."""
        return pd.read_sql("SELECT * FROM runs ORDER BY run_date DESC", self.conn)

    def get_latest_run_date(self) -> str:
        """Return the most recent run_date."""
        cursor = self.conn.execute(
            "SELECT run_date FROM runs ORDER BY run_date DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_run_dates(self) -> list:
        """Return all available run dates."""
        cursor = self.conn.execute(
            "SELECT run_date FROM runs ORDER BY run_date DESC"
        )
        return [row[0] for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
        print("[DB] Connection closed.")


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db = EtsyDB()

    runs = db.get_runs()
    print(f"\nRuns in DB: {len(runs)}")
    print(runs)

    db.close()
    