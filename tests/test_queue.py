import pytest

from queuedb import QueueConnection


@pytest.fixture
def connection():
    connection = QueueConnection(":memory:")
    connection.create()
    yield connection
    connection.close()


def test_enqueue(connection: QueueConnection):
    item1 = connection.enqueue("test")
    assert item1.name == "test"
    assert item1.position == 0

    item2 = connection.enqueue("test2")
    assert item2.name == "test2"
    assert item2.position == 1


def test_get_all_empty(connection: QueueConnection):
    assert connection.get_all() == []


def test_get_all(connection: QueueConnection):
    item1 = connection.enqueue("test")
    item2 = connection.enqueue("test2")
    assert connection.get_all() == [item1, item2]


def test_get_all_with_limit(connection: QueueConnection):
    items = [connection.enqueue(f"item{i}") for i in range(5)]
    assert connection.get_all(limit=3) == items[:3]


def test_get(connection: QueueConnection):
    items = [connection.enqueue("test{i}") for i in range(3)]
    assert items == [connection.get(item.id) for item in items]


def test_get_missing_returns_none(connection: QueueConnection):
    item = connection.enqueue("test")
    assert connection.get(item.id + 1) is None


def test_remove_missing(connection: QueueConnection):
    item = connection.enqueue("test")
    connection.remove(item.id + 1)


def test_remove(connection: QueueConnection):
    items = [connection.enqueue(f"item{i}") for i in range(3)]
    connection.remove(items[1].id)
    assert connection.get(items[1].id) is None


def test_all_ids_are_unique(connection: QueueConnection):
    items = [connection.enqueue(f"item{i}") for i in range(3)]
    assert len({item.id for item in items}) == 3


def test_all_ids_are_incremented(connection: QueueConnection):
    ids = [i.id for i in (connection.enqueue(f"item{i}") for i in range(3))]
    assert ids == sorted(ids)


def test_new_id_is_unique_after_removal(connection: QueueConnection):
    ids = [i.id for i in (connection.enqueue(f"item{i}") for i in range(3))]
    connection.remove(ids[-1])
    new = connection.enqueue("new")
    assert new.id not in ids
    assert new.position == 2


def test_positions_change_after_removal(connection: QueueConnection):
    items = [connection.enqueue(f"item{i}") for i in range(3)]
    connection.remove(items[1].id)
    assert connection.get_all() == [
        item.model_copy(update={'position': pos})
        for pos, item in enumerate((items[0], items[2]))
    ]


def test_tokens_are_unique(connection: QueueConnection):
    tokens = [connection.enqueue("item").token for _ in range(100)]
    assert len(set(tokens)) == len(tokens)
