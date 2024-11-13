from pathlib import Path

import pytest
from fastapi import status as Status
from fastapi.testclient import TestClient

from ticket_queue.app import app, get_queue_connection
from ticket_queue.ticket_queue import QueueConnection

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_get_queue_connection(tmp_path: Path):
    db_path = tmp_path / "queue.db"

    def override():
        with QueueConnection(db_path) as con:
            con.create()
            yield con

    app.dependency_overrides[get_queue_connection] = override
    yield
    app.dependency_overrides = {}


def test_new_ticket() -> None:
    ret = client.post("/api/tickets", json={"name": "test"})
    assert ret.status_code == Status.HTTP_201_CREATED

    data = ret.json()
    assert data["name"] == "test"


def test_new_ticket_orders() -> None:
    t1 = client.post("/api/tickets", json={"name": "t1"}).json()
    t2 = client.post("/api/tickets", json={"name": "t2"}).json()
    assert t1["position"] == 0
    assert t2["position"] == 1


def test_new_ticket_name_whitespace_stripped() -> None:
    data = client.post("/api/tickets", json={"name": "  \ttest \n"}).json()
    assert data["name"] == "test"


@pytest.mark.parametrize("name", ("", " ", "\n\t"))
def test_new_ticket_invalid_name_fails(name) -> None:
    ret = client.post("/api/tickets", json={"name": name})
    assert ret.status_code == Status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.fixture()
def new_ticket() -> dict:
    ret = client.post("/api/tickets", json={"name": "test"})
    return ret.json()


def test_get_ticket(new_ticket) -> None:
    id = new_ticket["id"]
    token = new_ticket["token"]
    ret = client.get(f"/api/ticket/{id}", params={"token": token})
    assert ret.status_code == Status.HTTP_200_OK
    assert new_ticket == ret.json()


def test_get_ticket_no_token_fails(new_ticket) -> None:
    ret = client.get(f"/api/ticket/{new_ticket['id']}")
    assert ret.status_code == Status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_ticket_invalid_token_fails(new_ticket) -> None:
    ret = client.get(
        f"/api/ticket/{new_ticket['id']}", params={"token": "abc"}
    )
    assert ret.status_code == Status.HTTP_404_NOT_FOUND


def test_delete_ticket(new_ticket) -> None:
    id = new_ticket["id"]
    token = new_ticket["token"]
    ret = client.delete(
        f"/api/ticket/{id}", headers={"Authorization": f"Token {token}"}
    )
    assert ret.status_code == Status.HTTP_204_NO_CONTENT

    ret = client.get(f"/api/ticket/{id}", params={"token": token})
    assert ret.status_code == Status.HTTP_404_NOT_FOUND


def test_delete_ticket_changes_position() -> None:
    t1 = client.post("/api/tickets", json={"name": "t1"}).json()
    t2 = client.post("/api/tickets", json={"name": "t2"}).json()
    client.delete(
        f"/api/ticket/{t1['id']}",
        headers={"Authorization": f"Token {t1['token']}"},
    )

    t2_new = client.get(
        f"/api/ticket/{t2['id']}", params={"token": t2["token"]}
    ).json()
    assert t2_new["position"] == 0


def test_delete_ticket_missing_authorization_fails(new_ticket) -> None:
    id = new_ticket["id"]
    ret = client.delete(f"/api/ticket/{id}")
    assert ret.status_code == Status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "header_fmt",
    (
        "{}",
        "Token",
        "Token{}",
        "token {}",
        "Token  {}",
        "Token {} ",
        "Token invalid",
        "Token {}invalid",
    ),
)
def test_delete_ticket_invalid_authorization_fails(
    header_fmt: str, new_ticket
) -> None:
    id = new_ticket["id"]
    ret = client.delete(
        f"/api/ticket/{id}",
        headers={"Authorization": header_fmt.format(new_ticket["token"])},
    )
    assert ret.status_code == Status.HTTP_401_UNAUTHORIZED
