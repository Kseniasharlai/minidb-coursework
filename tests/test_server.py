"""
Тести для REST API сервера (бонус Етапу 2).
Використовують вбудований Flask test_client — реальний HTTP-сервер піднімати не потрібно.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))

import pytest
from server.app import app as flask_app


@pytest.fixture
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        # скидаємо базу перед кожним тестом, щоб тести не залежали один від одного
        c.post("/api/database/new", json={"name": "test_db"})
        yield c


def test_create_table_and_add_row(client):
    resp = client.post(
        "/api/tables",
        json={"name": "t1", "columns": [{"name": "id", "type": "integer"}]},
    )
    assert resp.status_code == 201

    resp = client.post("/api/tables/t1/rows", json={"values": ["5"]})
    assert resp.status_code == 201
    assert resp.get_json()["row_count"] == 1


def test_add_row_invalid_value_returns_400(client):
    client.post("/api/tables", json={"name": "t1", "columns": [{"name": "id", "type": "integer"}]})
    resp = client.post("/api/tables/t1/rows", json={"values": ["not-a-number"]})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_intersect_over_http(client):
    cols = [{"name": "id", "type": "integer"}, {"name": "name", "type": "string"}]
    client.post("/api/tables", json={"name": "a", "columns": cols})
    client.post("/api/tables", json={"name": "b", "columns": cols})

    client.post("/api/tables/a/rows", json={"values": ["1", "Ivan"]})
    client.post("/api/tables/a/rows", json={"values": ["2", "Olena"]})
    client.post("/api/tables/b/rows", json={"values": ["2", "Olena"]})
    client.post("/api/tables/b/rows", json={"values": ["3", "Petro"]})

    resp = client.post("/api/intersect", json={"table1": "a", "table2": "b"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["row_count"] == 1
    assert data["rows"] == [["2", "Olena"]]
