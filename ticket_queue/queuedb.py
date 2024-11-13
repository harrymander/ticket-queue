import sqlite3
import uuid
from os import PathLike

from ticket_queue.models import QueueEntry


def gen_token() -> str:
    return uuid.uuid4().hex


class QueueConnection:
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
                    token NOT NULL
                )
            """)

    def enqueue(self, name: str) -> QueueEntry:
        if not name:
            raise ValueError("name must have a value")

        token = gen_token()
        with self.con:
            position, id = self.con.execute(
                """
                WITH count_query AS (
                    SELECT COUNT(*) AS count FROM queue
                )
                INSERT INTO queue (name, token)
                VALUES (?, ?)
                RETURNING (SELECT count FROM count_query) AS position, id;
                """,
                (name, token),
            ).fetchone()

        return QueueEntry(name=name, id=id, token=token, position=position - 1)

    def remove(self, id: int) -> None:
        with self.con:
            self.con.execute(
                """
                DELETE FROM queue WHERE ID = ?
                """,
                (id,),
            )

    def get_all(self, *, limit: int | None = None) -> list[QueueEntry]:
        if limit is not None:
            if limit <= 0:
                raise ValueError("limit must be greater than 0")
            limit_query = f"LIMIT {limit}"
        else:
            limit_query = ""

        with self.con:
            items = self.con.execute(f"""
                SELECT id, name, token
                FROM queue
                ORDER BY id
                {limit_query}
            """).fetchall()

        return [
            QueueEntry(id=id, name=name, token=token, position=pos)
            for pos, (id, name, token) in enumerate(items)
        ]

    def get(self, id: int) -> None | QueueEntry:
        with self.con:
            ret = self.con.execute(
                """
                SELECT name, token, position from (
                    SELECT
                        id,
                        name,
                        token,
                        ROW_NUMBER() OVER (ORDER BY id) AS position
                    FROM queue
                )
                WHERE id = ?
                """,
                (id,),
            ).fetchone()

        return (
            QueueEntry(
                name=ret[0],
                token=ret[1],
                position=ret[2] - 1,
                id=id,
            )
            if ret
            else None
        )
