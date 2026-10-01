# Міні-СУБД — навчальний проєкт

Часткова реалізація системи управління табличними базами даних (Тип 1).

**Варіант:** додаткові типи `picture` і `realInvl`; індивідуальна операція — **перетин таблиць**.

Проєкт виконано поетапно (модуль 1):

| Етап | Зміст | Звіт |
|---|---|---|
| 1 | UML-специфікація (8 діаграм) | [`docs/etap1-uml.md`](docs/etap1-uml.md) |
| 2 | Десктоп-клієнт + unit-тести + GUI (+ бонус: клієнт-сервер) | [`docs/etap2-zvit-povnyi.docx`](docs/etap2-zvit-povnyi.docx) |
| 3 | Веб-версія (REST) | [`docs/etap3-zvit.docx`](docs/etap3-zvit.docx) |
| 4 | Порівняльний аналіз десктоп vs веб | [`docs/etap4-zvit.docx`](docs/etap4-zvit.docx) |

## Структура репозиторію

```
minidb/
  core/            — ядро системи: типи полів, Table, Database, операція перетину
                     (не залежить від інтерфейсу — використовується всіма клієнтами)
  tests/
    test_core.py   — unit-тести ядра (pytest)
    test_server.py — тести REST API
  desktop_app/
    gui.py         — десктоп-клієнт (Tkinter), працює з локальним файлом
    gui_remote.py  — десктоп-клієнт, що працює через REST-сервер (бонус)
  server/
    app.py         — Flask REST API (обгортає core/, роздає web_app/ як веб-сторінку)
    run_server.py  — точка входу для запуску сервера
  web_app/         — веб-клієнт: index.html, style.css, app.js
  docs/            — звіти по кожному етапу
```

## Швидкий старт

### Десктоп-клієнт (локальний, без сервера)
```bash
python3 desktop_app/gui.py
```

### Сервер (потрібен для веб-клієнта і мережевого десктоп-клієнта)
```bash
pip install flask
python3 server/run_server.py
```
Сервер слухає на `http://127.0.0.1:5000` (або інший порт, якщо 5000 зайнятий — див. нижче).

### Веб-клієнт
Запустіть сервер (див. вище), тоді відкрийте в браузері:
```
http://127.0.0.1:5000/
```

### Десктоп-клієнт через сервер (бонус)
Термінал 1: `python3 server/run_server.py`
Термінал 2:
```bash
pip install requests
python3 desktop_app/gui_remote.py
```

### Тести
```bash
pip install pytest flask requests
pytest tests/ -v
```

## Технології

- **Ядро:** Python (стандартна бібліотека)
- **Десктоп GUI:** Tkinter
- **Сервер:** Flask (REST API)
- **Веб-клієнт:** HTML / CSS / JavaScript (без фреймворків, звертається до того самого REST API)

## Примітка щодо порту

На macOS порт 5000 часто зайнятий системною службою AirPlay Receiver. Якщо сервер
не стартує з помилкою `Address already in use`, змініть порт у `server/run_server.py`
(рядок `port=5000`) на будь-який вільний, наприклад `5050`, і відповідно відкривайте
`http://127.0.0.1:5050/`.
