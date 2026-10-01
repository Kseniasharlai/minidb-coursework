"""Точка входу для запуску REST API сервера міні-СУБД."""
from app import app

if __name__ == "__main__":
    print("Сервер міні-СУБД слухає на http://127.0.0.1:5050")
    print("Перевірка стану: GET http://127.0.0.1:5050/api/health")
    app.run(host="0.0.0.0", port=5050, debug=False)
