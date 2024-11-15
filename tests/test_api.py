import base64
from pathlib import Path

import pytest
from fastapi import status as Status
from fastapi.testclient import TestClient

from ticket_queue.api import api
from ticket_queue.config import Config, PathOrUrl
from ticket_queue.ticket_queue import QueueConnection

client = TestClient(api)


PLAINTEXT_ADMIN_PASSWORD = "admin"


@pytest.fixture()
def password(request) -> str:
    param = getattr(request, "param", None)
    if param is None:
        return PLAINTEXT_ADMIN_PASSWORD
    return param


@pytest.fixture(autouse=True)
def override_get_config(tmp_path: Path, password: str):
    from ticket_queue.api.dependencies import get_config

    database = str(tmp_path / "queue.db")
    config = Config(
        database=database,
        urls=["url"],
        admin_password=password,
        frontend=PathOrUrl(type=PathOrUrl.Path, value="don't care"),
    )
    with QueueConnection(database) as queue:
        queue.create()

    def override():
        return config

    api.dependency_overrides[get_config] = override
    yield
    api.dependency_overrides = {}


def test_new_ticket() -> None:
    ret = client.post("/tickets", json={"name": "test"})
    assert ret.status_code == Status.HTTP_201_CREATED

    data = ret.json()
    assert data["name"] == "test"


def test_new_ticket_orders() -> None:
    t1 = client.post("/tickets", json={"name": "t1"}).json()
    t2 = client.post("/tickets", json={"name": "t2"}).json()
    assert t1["position"] == 0
    assert t2["position"] == 1


def test_new_ticket_name_whitespace_stripped() -> None:
    data = client.post("/tickets", json={"name": "  \ttest \n"}).json()
    assert data["name"] == "test"


@pytest.mark.parametrize("name", ("", " ", "\n\t"))
def test_new_ticket_invalid_name_fails(name) -> None:
    ret = client.post("/tickets", json={"name": name})
    assert ret.status_code == Status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.fixture()
def new_ticket() -> dict:
    ret = client.post("/tickets", json={"name": "test"})
    return ret.json()


def test_get_ticket(new_ticket) -> None:
    id = new_ticket["id"]
    token = new_ticket["token"]
    ret = client.get(f"/ticket/{id}", params={"token": token})
    assert ret.status_code == Status.HTTP_200_OK
    assert new_ticket == ret.json()


def test_get_ticket_no_token_fails(new_ticket) -> None:
    ret = client.get(f"/ticket/{new_ticket['id']}")
    assert ret.status_code == Status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_ticket_invalid_token_fails(new_ticket) -> None:
    ret = client.get(f"/ticket/{new_ticket['id']}", params={"token": "abc"})
    assert ret.status_code == Status.HTTP_404_NOT_FOUND


def test_delete_ticket(new_ticket) -> None:
    id = new_ticket["id"]
    token = new_ticket["token"]
    ret = client.delete(
        f"/ticket/{id}", headers={"Authorization": f"Token {token}"}
    )
    assert ret.status_code == Status.HTTP_204_NO_CONTENT

    ret = client.get(f"/ticket/{id}", params={"token": token})
    assert ret.status_code == Status.HTTP_404_NOT_FOUND


def test_delete_ticket_changes_position() -> None:
    t1 = client.post("/tickets", json={"name": "t1"}).json()
    t2 = client.post("/tickets", json={"name": "t2"}).json()
    client.delete(
        f"/ticket/{t1['id']}",
        headers={"Authorization": f"Token {t1['token']}"},
    )

    t2_new = client.get(
        f"/ticket/{t2['id']}", params={"token": t2["token"]}
    ).json()
    assert t2_new["position"] == 0


def test_delete_ticket_missing_authorization_fails(new_ticket) -> None:
    id = new_ticket["id"]
    ret = client.delete(f"/ticket/{id}")
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
        f"/ticket/{id}",
        headers={"Authorization": header_fmt.format(new_ticket["token"])},
    )
    assert ret.status_code == Status.HTTP_401_UNAUTHORIZED


ENCODED_PASSWORD = base64.b64encode(PLAINTEXT_ADMIN_PASSWORD.encode()).decode(
    "ascii"
)
PASSWORD_AUTH_HEADER = {"Authorization": f"Password {ENCODED_PASSWORD}"}
INVALID_UTF8 = base64.b64encode(b"\x00\x00").decode()


def parametrize_invalid_password_auth_header(name="header"):
    invalid_header_vals = (
        f"password {ENCODED_PASSWORD}",
        f"Password  {ENCODED_PASSWORD}",
        f"Password {ENCODED_PASSWORD} ",
        f"Password {ENCODED_PASSWORD.rstrip('=')}",
        f"Password {ENCODED_PASSWORD}invalid",
        f"Password ={ENCODED_PASSWORD}",
        "Password invalid",
        "Password",
        ENCODED_PASSWORD,
        f"Password {PLAINTEXT_ADMIN_PASSWORD}",
        f"Password {INVALID_UTF8}",
    )
    return pytest.mark.parametrize(
        name,
        [{"Authorization": val} for val in invalid_header_vals] + [{}],
        ids=invalid_header_vals + ("[missing]",),
    )


@pytest.fixture()
def tickets() -> list[dict]:
    return [
        client.post("/tickets", json={"name": f"t{i}"}).json()
        for i in range(5)
    ]


def test_admin_get_no_tickets() -> None:
    ret = client.get("/admin/tickets", headers=PASSWORD_AUTH_HEADER)
    assert ret.status_code == Status.HTTP_200_OK
    assert ret.json() == []


def test_admin_get_tickets(tickets) -> None:
    all_tickets = client.get(
        "/admin/tickets",
        headers=PASSWORD_AUTH_HEADER,
    )
    assert all_tickets.status_code == Status.HTTP_200_OK
    assert all_tickets.json() == tickets


@pytest.mark.parametrize("password", ("",), indirect=True)
def test_admin_get_tickets_with_empty_password():
    ret = client.get("/admin/tickets", headers={"Authorization": "Password"})
    assert ret.status_code == 200


@parametrize_invalid_password_auth_header()
def test_admin_get_tickets_invalid_header_fails(header):
    ret = client.get("/admin/tickets", headers=header)
    assert ret.status_code == Status.HTTP_401_UNAUTHORIZED


def test_admin_get_individual_ticket(tickets) -> None:
    for ticket in tickets:
        ret = client.get(
            f"/admin/ticket/{ticket['id']}",
            headers=PASSWORD_AUTH_HEADER,
        )
        assert ret.status_code == Status.HTTP_200_OK
        assert ret.json() == ticket


def test_admin_get_individual_ticket_missing(tickets) -> None:
    ret = client.get(
        f"/admin/ticket/{tickets[-1]['id'] + 1}",
        headers=PASSWORD_AUTH_HEADER,
    )
    assert ret.status_code == Status.HTTP_404_NOT_FOUND


@parametrize_invalid_password_auth_header()
def test_admin_get_individual_ticket_invalid_header_fails(new_ticket, header):
    ret = client.get(f"/admin/ticket/{new_ticket['id']}", headers=header)
    assert ret.status_code == Status.HTTP_401_UNAUTHORIZED


def test_admin_delete_tickets(tickets) -> None:
    to_delete = tickets.pop(len(tickets) // 2)
    ret = client.delete(
        f"/admin/ticket/{to_delete['id']}", headers=PASSWORD_AUTH_HEADER
    )
    assert ret.status_code == Status.HTTP_204_NO_CONTENT

    all_tickets = client.get(
        "/admin/tickets", headers=PASSWORD_AUTH_HEADER
    ).json()
    assert all_tickets == [
        ticket | {"position": new_pos}
        for new_pos, ticket in enumerate(tickets)
    ]


@parametrize_invalid_password_auth_header()
def test_admin_delete_individual_ticket_invalid_header_fails(
    new_ticket, header
):
    ret = client.delete(f"/admin/ticket/{new_ticket['id']}", headers=header)
    assert ret.status_code == Status.HTTP_401_UNAUTHORIZED
