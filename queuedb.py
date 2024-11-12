import sqlite3
from os import PathLike

from models import QueueEntry


class QueueConnection:
    def __init__(self, path: str | PathLike):
        self.con = sqlite3.connect(path)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> 'QueueConnection':
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def create(self) -> None:
        with self.con:
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name NOT NULL
                )
            """)

    def enqueue(self, name: str) -> QueueEntry:
        if not name:
            raise ValueError('name must have a value')

        with self.con:
            position, id = self.con.execute(
                """
                WITH count_query AS (
                    SELECT COUNT(*) AS count FROM queue
                )
                INSERT INTO queue (name)
                VALUES (?)
                RETURNING (SELECT count FROM count_query) AS position, id;
                """,
                (name,)
            ).fetchone()

        return QueueEntry(name=name, id=id, position=position - 1)

    def remove(self, id: int) -> None:
        with self.con:
            self.con.execute(
                """
                DELETE FROM queue WHERE ID = ?
                """,
                (id,)
            )

    def get_all(self, *, limit: int | None = None) -> list[QueueEntry]:
        if limit is not None:
            if limit <= 0:
                raise ValueError('limit must be greater than 0')
            limit_query = f"LIMIT {limit}"
        else:
            limit_query = ""

        with self.con:
            items = self.con.execute(f"""
                SELECT id, name
                FROM queue
                ORDER BY id
                {limit_query}
            """).fetchall()

        return [
            QueueEntry(id=id, position=pos, name=name)
            for pos, (id, name) in enumerate(items)
        ]

    def get(self, id: int) -> None | QueueEntry:
        with self.con:
            ret = self.con.execute(
                """
                SELECT position, name from (
                    SELECT
                        id,
                        name,
                        ROW_NUMBER() OVER (ORDER BY id) AS position
                    FROM queue
                )
                WHERE id = ?
                """,
                (id,)
            ).fetchone()

        return QueueEntry(
            position=ret[0] - 1,
            id=id,
            name=ret[1],
        ) if ret else None
