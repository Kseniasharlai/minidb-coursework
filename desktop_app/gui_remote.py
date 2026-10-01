"""
БОНУС Етапу 2: десктоп-клієнт, що взаємодіє з віддаленим сервером.

На відміну від desktop_app/gui.py (працює з локальним об'єктом Database і локальним
файлом), цей клієнт не містить жодної бізнес-логіки — усі операції (валідація,
створення таблиць, перетин) виконуються на сервері (server/app.py). GUI лише
надсилає HTTP-запити через бібліотеку requests і відображає відповіді.

Запуск:
  1) термінал 1: python3 server/run_server.py
  2) термінал 2: python3 desktop_app/gui_remote.py [--host 127.0.0.1] [--port 5000]
"""

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TYPE_NAMES = ["integer", "real", "char", "string", "picture", "realInvl"]


class ApiClient:
    """Тонка обгортка над REST API сервера — жодної бізнес-логіки, лише HTTP-виклики."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _handle(self, resp: requests.Response):
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("error", resp.text)
            except ValueError:
                msg = resp.text
            raise RuntimeError(msg)
        return resp.json()

    def health(self):
        return self._handle(requests.get(self._url("/api/health"), timeout=5))

    def new_database(self, name: str):
        return self._handle(
            requests.post(self._url("/api/database/new"), json={"name": name}, timeout=5)
        )

    def save_database(self, path: str):
        return self._handle(
            requests.post(self._url("/api/database/save"), json={"path": path}, timeout=5)
        )

    def load_database(self, path: str):
        return self._handle(
            requests.post(self._url("/api/database/load"), json={"path": path}, timeout=5)
        )

    def list_tables(self):
        return self._handle(requests.get(self._url("/api/tables"), timeout=5))["tables"]

    def create_table(self, name: str, columns: list):
        return self._handle(
            requests.post(
                self._url("/api/tables"),
                json={"name": name, "columns": columns},
                timeout=5,
            )
        )

    def drop_table(self, name: str):
        return self._handle(requests.delete(self._url(f"/api/tables/{name}"), timeout=5))

    def get_table(self, name: str):
        return self._handle(requests.get(self._url(f"/api/tables/{name}"), timeout=5))

    def add_row(self, table: str, values: list):
        return self._handle(
            requests.post(
                self._url(f"/api/tables/{table}/rows"), json={"values": values}, timeout=5
            )
        )

    def edit_row(self, table: str, index: int, values: list):
        return self._handle(
            requests.put(
                self._url(f"/api/tables/{table}/rows/{index}"),
                json={"values": values},
                timeout=5,
            )
        )

    def delete_row(self, table: str, index: int):
        return self._handle(
            requests.delete(self._url(f"/api/tables/{table}/rows/{index}"), timeout=5)
        )

    def intersect(self, table1: str, table2: str):
        return self._handle(
            requests.post(
                self._url("/api/intersect"),
                json={"table1": table1, "table2": table2},
                timeout=5,
            )
        )


class CreateTableDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Створити таблицю (на сервері)")
        self.result = None
        self.column_rows = []

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Ім'я таблиці:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var, width=30).grid(row=0, column=1, columnspan=2, sticky="we")

        self.columns_frame = ttk.LabelFrame(frm, text="Колонки")
        self.columns_frame.grid(row=1, column=0, columnspan=3, pady=8, sticky="we")

        ttk.Button(frm, text="+ Додати колонку", command=self.add_column_row).grid(row=2, column=0, sticky="w", pady=4)
        ttk.Button(frm, text="Створити", command=self.on_submit).grid(row=3, column=1, pady=8)
        ttk.Button(frm, text="Скасувати", command=self.destroy).grid(row=3, column=2, pady=8)

        self.add_column_row()
        self.grab_set()

    def add_column_row(self):
        row_idx = len(self.column_rows)
        name_var = tk.StringVar()
        type_var = tk.StringVar(value=TYPE_NAMES[0])
        ttk.Entry(self.columns_frame, textvariable=name_var, width=16).grid(row=row_idx, column=0, padx=4, pady=2)
        ttk.Combobox(self.columns_frame, textvariable=type_var, values=TYPE_NAMES, width=12, state="readonly").grid(
            row=row_idx, column=1, padx=4, pady=2
        )
        self.column_rows.append((name_var, type_var))

    def on_submit(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка", "Вкажіть ім'я таблиці")
            return
        columns = []
        for name_var, type_var in self.column_rows:
            cname = name_var.get().strip()
            if cname:
                columns.append({"name": cname, "type": type_var.get()})
        if not columns:
            messagebox.showerror("Помилка", "Додайте хоча б одну колонку")
            return
        self.result = (name, columns)
        self.destroy()


class RowDialog(tk.Toplevel):
    def __init__(self, master, columns: list, initial_values=None):
        super().__init__(master)
        self.title("Рядок таблиці")
        self.result = None
        self.vars = []

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        for i, col in enumerate(columns):
            ttk.Label(frm, text=f"{col['name']} ({col['type']}):").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=str(initial_values[i]) if initial_values else "")
            ttk.Entry(frm, textvariable=var, width=30).grid(row=i, column=1, pady=2, padx=6)
            self.vars.append(var)

        btn_row = len(columns)
        ttk.Button(frm, text="Зберегти", command=self.on_submit).grid(row=btn_row, column=0, pady=10)
        ttk.Button(frm, text="Скасувати", command=self.destroy).grid(row=btn_row, column=1, pady=10)
        self.grab_set()

    def on_submit(self):
        self.result = [v.get() for v in self.vars]
        self.destroy()


class IntersectDialog(tk.Toplevel):
    def __init__(self, master, table_names):
        super().__init__(master)
        self.title("Перетин таблиць (на сервері)")
        self.result = None

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Таблиця 1:").grid(row=0, column=0, sticky="w")
        self.t1_var = tk.StringVar(value=table_names[0] if table_names else "")
        ttk.Combobox(frm, textvariable=self.t1_var, values=table_names, state="readonly", width=20).grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="Таблиця 2:").grid(row=1, column=0, sticky="w")
        self.t2_var = tk.StringVar(value=table_names[-1] if table_names else "")
        ttk.Combobox(frm, textvariable=self.t2_var, values=table_names, state="readonly", width=20).grid(row=1, column=1, pady=4)

        ttk.Button(frm, text="Виконати перетин на сервері", command=self.on_submit).grid(row=2, column=0, columnspan=2, pady=10)
        self.grab_set()

    def on_submit(self):
        if self.t1_var.get() == self.t2_var.get():
            messagebox.showerror("Помилка", "Оберіть дві різні таблиці")
            return
        self.result = (self.t1_var.get(), self.t2_var.get())
        self.destroy()


class RemoteMainApp(tk.Tk):
    def __init__(self, server_url: str):
        super().__init__()
        self.title(f"Міні-СУБД — десктоп-клієнт (ВІДДАЛЕНИЙ СЕРВЕР: {server_url})")
        self.geometry("950x540")

        self.api = ApiClient(server_url)
        self.current_table_name = None
        self.current_table_columns = []

        self._build_menu()
        self._build_layout()
        self._check_connection()
        self._refresh_table_list()

    def _check_connection(self):
        try:
            info = self.api.health()
            self.status_var_init = f"Підключено до сервера. База на сервері: '{info['database']}'"
        except requests.exceptions.RequestException as e:
            messagebox.showerror(
                "Немає з'єднання з сервером",
                f"Не вдалося підключитись до {self.api.base_url}.\n"
                f"Переконайтесь, що сервер запущено (python3 server/run_server.py).\n\n{e}",
            )
            self.status_var_init = "Немає з'єднання із сервером"

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Нова база (на сервері)", command=self.new_database)
        file_menu.add_command(label="Зберегти базу на сервері...", command=self.save_database)
        file_menu.add_command(label="Завантажити базу на сервері...", command=self.open_database)
        file_menu.add_separator()
        file_menu.add_command(label="Вихід", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

    def _build_layout(self):
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Таблиці бази (сервер):").pack(anchor="w")
        self.table_listbox = tk.Listbox(left, width=26, height=20)
        self.table_listbox.pack(fill="y", expand=True, pady=4)
        self.table_listbox.bind("<<ListboxSelect>>", self.on_select_table)

        ttk.Button(left, text="Створити таблицю", command=self.create_table).pack(fill="x", pady=2)
        ttk.Button(left, text="Знищити таблицю", command=self.drop_table).pack(fill="x", pady=2)
        ttk.Button(left, text="Перетин таблиць", command=self.do_intersect).pack(fill="x", pady=(12, 2))
        ttk.Button(left, text="Оновити з сервера", command=self._refresh_table_list).pack(fill="x", pady=2)

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(right, show="headings")
        self.tree.pack(fill="both", expand=True)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Додати рядок", command=self.add_row).pack(side="left", padx=2)
        ttk.Button(btns, text="Редагувати рядок", command=self.edit_row).pack(side="left", padx=2)
        ttk.Button(btns, text="Видалити рядок", command=self.delete_row).pack(side="left", padx=2)

        self.status_var = tk.StringVar(value="Ініціалізація...")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(side="bottom", fill="x")
        self.after(100, lambda: self.status_var.set(getattr(self, "status_var_init", "Готово")))

    def new_database(self):
        name = simpledialog.askstring("Нова база на сервері", "Ім'я бази:", initialvalue="server_db")
        if name:
            try:
                self.api.new_database(name)
                self.current_table_name = None
                self._refresh_table_list()
                self._refresh_tree()
                self.status_var.set(f"На сервері створено нову базу '{name}'")
            except RuntimeError as e:
                messagebox.showerror("Помилка сервера", str(e))

    def save_database(self):
        path = simpledialog.askstring("Зберегти на сервері", "Шлях на СЕРВЕРІ (не на вашому Mac!):",
                                       initialvalue="/tmp/server_db.json")
        if path:
            try:
                self.api.save_database(path)
                self.status_var.set(f"Базу збережено на сервері: {path}")
            except RuntimeError as e:
                messagebox.showerror("Помилка сервера", str(e))

    def open_database(self):
        path = simpledialog.askstring("Завантажити з сервера", "Шлях на СЕРВЕРІ:",
                                       initialvalue="/tmp/server_db.json")
        if path:
            try:
                self.api.load_database(path)
                self.current_table_name = None
                self._refresh_table_list()
                self._refresh_tree()
                self.status_var.set(f"Базу завантажено з сервера: {path}")
            except RuntimeError as e:
                messagebox.showerror("Помилка сервера", str(e))

    def create_table(self):
        dlg = CreateTableDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            name, columns = dlg.result
            try:
                self.api.create_table(name, columns)
                self._refresh_table_list()
                self.status_var.set(f"Таблицю '{name}' створено на сервері")
            except RuntimeError as e:
                messagebox.showerror("Помилка сервера", str(e))

    def drop_table(self):
        if not self.current_table_name:
            messagebox.showinfo("Інфо", "Оберіть таблицю зі списку")
            return
        if messagebox.askyesno("Підтвердження", f"Знищити таблицю '{self.current_table_name}' на сервері?"):
            try:
                self.api.drop_table(self.current_table_name)
                self.current_table_name = None
                self._refresh_table_list()
                self._refresh_tree()
            except RuntimeError as e:
                messagebox.showerror("Помилка сервера", str(e))

    def do_intersect(self):
        names = self.api.list_tables()
        if len(names) < 2:
            messagebox.showinfo("Інфо", "Потрібно щонайменше 2 таблиці для перетину")
            return
        dlg = IntersectDialog(self, names)
        self.wait_window(dlg)
        if dlg.result:
            n1, n2 = dlg.result
            try:
                result = self.api.intersect(n1, n2)
                self._refresh_table_list()
                messagebox.showinfo(
                    "Готово",
                    f"Перетин виконано НА СЕРВЕРІ: {result['row_count']} спільних рядків.\n"
                    f"Результат у таблиці '{result['result_table']}'.",
                )
            except RuntimeError as e:
                messagebox.showerror("Помилка сервера", str(e))

    def add_row(self):
        if not self.current_table_name:
            messagebox.showinfo("Інфо", "Оберіть таблицю зі списку")
            return
        dlg = RowDialog(self, self.current_table_columns)
        self.wait_window(dlg)
        if dlg.result:
            try:
                self.api.add_row(self.current_table_name, dlg.result)
                self._refresh_tree()
            except RuntimeError as e:
                messagebox.showerror("Помилка валідації (від сервера)", str(e))

    def edit_row(self):
        sel = self.tree.selection()
        if not self.current_table_name or not sel:
            messagebox.showinfo("Інфо", "Оберіть рядок для редагування")
            return
        index = self.tree.index(sel[0])
        current_values = self.tree.item(sel[0])["values"]
        dlg = RowDialog(self, self.current_table_columns, initial_values=current_values)
        self.wait_window(dlg)
        if dlg.result:
            try:
                self.api.edit_row(self.current_table_name, index, dlg.result)
                self._refresh_tree()
            except RuntimeError as e:
                messagebox.showerror("Помилка валідації (від сервера)", str(e))

    def delete_row(self):
        sel = self.tree.selection()
        if not self.current_table_name or not sel:
            return
        index = self.tree.index(sel[0])
        try:
            self.api.delete_row(self.current_table_name, index)
            self._refresh_tree()
        except RuntimeError as e:
            messagebox.showerror("Помилка сервера", str(e))

    def _refresh_table_list(self):
        try:
            names = self.api.list_tables()
        except RuntimeError as e:
            messagebox.showerror("Помилка сервера", str(e))
            return
        self.table_listbox.delete(0, tk.END)
        for name in names:
            self.table_listbox.insert(tk.END, name)

    def on_select_table(self, event):
        sel = self.table_listbox.curselection()
        if not sel:
            return
        name = self.table_listbox.get(sel[0])
        self.current_table_name = name
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.current_table_name:
            self.tree["columns"] = []
            return
        try:
            data = self.api.get_table(self.current_table_name)
        except RuntimeError as e:
            messagebox.showerror("Помилка сервера", str(e))
            return
        self.current_table_columns = data["columns"]
        col_names = [c["name"] for c in data["columns"]]
        self.tree["columns"] = col_names
        for c in col_names:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120)
        for row in data["rows"]:
            self.tree.insert("", tk.END, values=row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Десктоп-клієнт міні-СУБД (робота через сервер)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="5000")
    args = parser.parse_args()

    server_url = f"http://{args.host}:{args.port}"
    app = RemoteMainApp(server_url)
    app.mainloop()
