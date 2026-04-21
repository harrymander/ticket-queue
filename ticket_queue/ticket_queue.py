import sqlite3
import time
import uuid
from os import PathLike

from ticket_queue.models import QueueTicket


def gen_token() -> str:
    return uuid.uuid4().hex


class QueueConnection:
    ANNOUNCEMENT_KEY = "announcement_message"

    def __init__(self, path: str | PathLike):
        self.con = sqlite3.connect(path)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "QueueConnection":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def create(self) -> None:
        with self.con:
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name NOT NULL,
                    token NOT NULL,
                    timestamp INTEGER NOT NULL
                )
            """)
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

    def set_announcement(self, message: str | None) -> None:
        value = message.strip() if message else ""
        with self.con:
            if value:
                self.con.execute(
                    """
                    INSERT INTO settings (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (self.ANNOUNCEMENT_KEY, value),
                )
            else:
                self.con.execute(
                    "DELETE FROM settings WHERE key = ?",
                    (self.ANNOUNCEMENT_KEY,),
                )

    def get_announcement(self) -> str | None:
        with self.con:
            ret = self.con.execute(
                "SELECT value FROM settings WHERE key = ?",
                (self.ANNOUNCEMENT_KEY,),
            ).fetchone()
        return ret[0] if ret else None

    def enqueue(self, name: str) -> QueueTicket:
        if not name:
            raise ValueError("name must have a value")

        token = gen_token()
        timestamp = int(time.time())
        with self.con:
            position, id = self.con.execute(
                """
                WITH count_query AS (
                    SELECT COUNT(*) AS count FROM queue
                )
                INSERT INTO queue (name, token, timestamp)
                VALUES (?, ?, ?)
                RETURNING (SELECT count FROM count_query) AS position, id;
                """,
                (name, token, timestamp),
            ).fetchone()

        return QueueTicket(
            name=name,
            id=id,
            token=token,
            position=position - 1,
            timestamp=timestamp,
        )

    def remove(self, id: int) -> None:
        with self.con:
            self.con.execute(
                """
                DELETE FROM queue WHERE ID = ?
                """,
                (id,),
            )

    def get_all(self, *, limit: int | None = None) -> list[QueueTicket]:
        if limit is not None:
            if limit <= 0:
                raise ValueError("limit must be greater than 0")
            limit_query = f"LIMIT {limit}"
        else:
            limit_query = ""

        with self.con:
            items = self.con.execute(f"""
                SELECT id, name, token, timestamp
                FROM queue
                ORDER BY id
                {limit_query}
            """).fetchall()

        return [
            QueueTicket(
                id=id,
                name=name,
                token=token,
                timestamp=timestamp,
                position=pos,
            )
            for pos, (id, name, token, timestamp) in enumerate(items)
        ]

    def get(self, id: int) -> None | QueueTicket:
        with self.con:
            ret = self.con.execute(
                """
                SELECT name, token, timestamp, position from (
                    SELECT
                        id,
                        name,
                        token,
                        timestamp,
                        ROW_NUMBER() OVER (ORDER BY id) AS position
                    FROM queue
                )
                WHERE id = ?
                """,
                (id,),
            ).fetchone()

        return (
            QueueTicket(
                name=ret[0],
                token=ret[1],
                timestamp=ret[2],
                position=ret[3] - 1,
                id=id,
            )
            if ret
            else None
        )
