"""
REST API сервер для міні-СУБД (БОНУС Етапу 2).

Сервер загортає вже готове ядро (core/) у HTTP-інтерфейс, щоб десктоп-клієнт міг
працювати не з локальним файлом, а через мережу — так, як показано на діаграмі
розгортання (Етап 1, п. 2.3, вузол "Веб-сервер").

Запуск:  python3 server/run_server.py
За замовчуванням слухає на http://127.0.0.1:5000
"""

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

from core.database import Database, DatabaseError
from core.table import Column, TableError
from core.types import create_type, FieldTypeError
from core.operations import intersect

# web_app/ містить веб-версію GUI (Етап 3) — статичні HTML/CSS/JS файли,
# що звертаються до цього самого REST API
_WEB_APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_app")

app = Flask(__name__, static_folder=_WEB_APP_DIR, static_url_path="")


@app.route("/")
def index():
    return app.send_static_file("index.html")

# Один спільний екземпляр бази на сервері (спрощення для навчального проєкту —
# без багатокористувацьких сесій; для реального продукту тут була б сесія/автентифікація)
db = Database("server_db")


def error_response(message: str, code: int = 400):
    return jsonify({"error": message}), code


# ---------------------------------------------------------------------------
# Управління базою
# ---------------------------------------------------------------------------

@app.route("/api/database/new", methods=["POST"])
def new_database():
    global db
    data = request.get_json(force=True) or {}
    db = Database(data.get("name", "server_db"))
    return jsonify({"name": db.name, "tables": db.list_tables()})


@app.route("/api/database/save", methods=["POST"])
def save_database():
    data = request.get_json(force=True) or {}
    path = data.get("path")
    if not path:
        return error_response("Не вказано 'path'")
    try:
        db.save(path)
    except OSError as e:
        return error_response(str(e), 500)
    return jsonify({"status": "saved", "path": path})


@app.route("/api/database/load", methods=["POST"])
def load_database():
    global db
    data = request.get_json(force=True) or {}
    path = data.get("path")
    if not path:
        return error_response("Не вказано 'path'")
    try:
        db = Database.load(path)
    except DatabaseError as e:
        return error_response(str(e), 404)
    return jsonify({"name": db.name, "tables": db.list_tables()})


# ---------------------------------------------------------------------------
# Управління таблицями
# ---------------------------------------------------------------------------

@app.route("/api/tables", methods=["GET"])
def list_tables():
    return jsonify({"tables": db.list_tables()})


@app.route("/api/tables", methods=["POST"])
def create_table():
    data = request.get_json(force=True) or {}
    name = data.get("name")
    columns_raw = data.get("columns", [])
    if not name or not columns_raw:
        return error_response("Потрібні поля 'name' і непорожній 'columns'")
    try:
        columns = [Column(c["name"], create_type(c["type"])) for c in columns_raw]
        db.create_table(name, columns)
    except (DatabaseError, FieldTypeError, KeyError) as e:
        return error_response(str(e))
    return jsonify({"status": "created", "name": name}), 201


@app.route("/api/tables/<name>", methods=["DELETE"])
def drop_table(name):
    try:
        db.drop_table(name)
    except DatabaseError as e:
        return error_response(str(e), 404)
    return jsonify({"status": "dropped", "name": name})


@app.route("/api/tables/<name>", methods=["GET"])
def get_table(name):
    try:
        table = db.get_table(name)
    except DatabaseError as e:
        return error_response(str(e), 404)
    return jsonify(
        {
            "name": table.name,
            "columns": [{"name": c.name, "type": c.type.name} for c in table.columns],
            "rows": table.get_rows_as_strings(),
        }
    )


# ---------------------------------------------------------------------------
# CRUD рядків
# ---------------------------------------------------------------------------

@app.route("/api/tables/<name>/rows", methods=["POST"])
def add_row(name):
    data = request.get_json(force=True) or {}
    values = data.get("values")
    if values is None:
        return error_response("Потрібне поле 'values'")
    try:
        table = db.get_table(name)
        table.add_row(values)
    except DatabaseError as e:
        return error_response(str(e), 404)
    except (FieldTypeError, TableError) as e:
        return error_response(str(e))
    return jsonify({"status": "row added", "row_count": len(table.rows)}), 201


@app.route("/api/tables/<name>/rows/<int:index>", methods=["PUT"])
def edit_row(name, index):
    data = request.get_json(force=True) or {}
    values = data.get("values")
    if values is None:
        return error_response("Потрібне поле 'values'")
    try:
        table = db.get_table(name)
        table.edit_row(index, values)
    except DatabaseError as e:
        return error_response(str(e), 404)
    except (FieldTypeError, TableError) as e:
        return error_response(str(e))
    return jsonify({"status": "row updated"})


@app.route("/api/tables/<name>/rows/<int:index>", methods=["DELETE"])
def delete_row(name, index):
    try:
        table = db.get_table(name)
        table.delete_row(index)
    except DatabaseError as e:
        return error_response(str(e), 404)
    except TableError as e:
        return error_response(str(e))
    return jsonify({"status": "row deleted"})


# ---------------------------------------------------------------------------
# Індивідуальна операція варіанту: перетин таблиць (через мережу)
# ---------------------------------------------------------------------------

@app.route("/api/intersect", methods=["POST"])
def do_intersect():
    data = request.get_json(force=True) or {}
    t1_name, t2_name = data.get("table1"), data.get("table2")
    if not t1_name or not t2_name:
        return error_response("Потрібні поля 'table1' і 'table2'")
    try:
        t1, t2 = db.get_table(t1_name), db.get_table(t2_name)
        result = intersect(t1, t2)
        db.tables[result.name] = result
    except DatabaseError as e:
        return error_response(str(e), 404)
    except TableError as e:
        return error_response(str(e))
    return jsonify(
        {
            "result_table": result.name,
            "row_count": len(result.rows),
            "rows": result.get_rows_as_strings(),
        }
    ), 201


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "database": db.name})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
