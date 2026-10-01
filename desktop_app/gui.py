"""
Десктоп GUI для міні-СУБД (Tkinter).

Запуск:  python3 desktop_app/gui.py   (з кореневої директорії проєкту minidb/)

Функціонал:
  - створення / знищення бази і таблиць
  - перегляд, додавання, редагування рядків з валідацією
  - збереження бази на диск та зчитування з диску
  - виконання індивідуальної операції варіанту: перетин таблиць
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.types import TYPE_REGISTRY, create_type, FieldTypeError
from core.table import Column, Table, TableError
from core.database import Database, DatabaseError
from core.operations import intersect


TYPE_NAMES = list(TYPE_REGISTRY.keys())  # ['integer', 'real', 'char', 'string', 'picture', 'realInvl']


class CreateTableDialog(tk.Toplevel):
    """Діалог створення нової таблиці: ім'я + динамічний список колонок."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Створити таблицю")
        self.result = None  # (name, [Column, ...])
        self.column_rows = []

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Ім'я таблиці:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var, width=30).grid(row=0, column=1, columnspan=2, sticky="we")

        self.columns_frame = ttk.LabelFrame(frm, text="Колонки")
        self.columns_frame.grid(row=1, column=0, columnspan=3, pady=8, sticky="we")

        ttk.Button(frm, text="+ Додати колонку", command=self.add_column_row).grid(
            row=2, column=0, sticky="w", pady=4
        )
        ttk.Button(frm, text="Створити", command=self.on_submit).grid(row=3, column=1, pady=8)
        ttk.Button(frm, text="Скасувати", command=self.destroy).grid(row=3, column=2, pady=8)

        self.add_column_row()
        self.grab_set()

    def add_column_row(self):
        row_idx = len(self.column_rows)
        name_var = tk.StringVar()
        type_var = tk.StringVar(value=TYPE_NAMES[0])
        ttk.Entry(self.columns_frame, textvariable=name_var, width=16).grid(row=row_idx, column=0, padx=4, pady=2)
        ttk.Combobox(
            self.columns_frame, textvariable=type_var, values=TYPE_NAMES, width=12, state="readonly"
        ).grid(row=row_idx, column=1, padx=4, pady=2)
        self.column_rows.append((name_var, type_var))

    def on_submit(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка", "Вкажіть ім'я таблиці")
            return
        columns = []
        for name_var, type_var in self.column_rows:
            cname = name_var.get().strip()
            if not cname:
                continue
            try:
                # picture-тип у GUI без обов'язкової перевірки існування файлу під час схеми
                ftype = create_type(type_var.get())
                if type_var.get() == "picture":
                    ftype.check_exists = False
                columns.append(Column(cname, ftype))
            except FieldTypeError as e:
                messagebox.showerror("Помилка", str(e))
                return
        if not columns:
            messagebox.showerror("Помилка", "Додайте хоча б одну колонку")
            return
        self.result = (name, columns)
        self.destroy()


class RowDialog(tk.Toplevel):
    """Діалог додавання/редагування рядка таблиці за її схемою."""

    def __init__(self, master, table: Table, initial_values=None):
        super().__init__(master)
        self.title("Рядок таблиці")
        self.table = table
        self.result = None
        self.vars = []

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        for i, col in enumerate(table.columns):
            ttk.Label(frm, text=f"{col.name} ({col.type.name}):").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=str(initial_values[i]) if initial_values else "")
            ttk.Entry(frm, textvariable=var, width=30).grid(row=i, column=1, pady=2, padx=6)
            self.vars.append(var)

        btn_row = len(table.columns)
        ttk.Button(frm, text="Зберегти", command=self.on_submit).grid(row=btn_row, column=0, pady=10)
        ttk.Button(frm, text="Скасувати", command=self.destroy).grid(row=btn_row, column=1, pady=10)

        self.grab_set()

    def on_submit(self):
        raw_values = [v.get() for v in self.vars]
        if not self.table.validate_row(raw_values):
            errors = []
            for col, raw in zip(self.table.columns, raw_values):
                if not col.type.validate(raw):
                    errors.append(f"  - '{col.name}' ({col.type.name}): некоректне значення '{raw}'")
            messagebox.showerror("Помилка валідації", "Виявлено помилки:\n" + "\n".join(errors))
            return
        self.result = raw_values
        self.destroy()


class IntersectDialog(tk.Toplevel):
    """Діалог вибору двох таблиць для виконання перетину."""

    def __init__(self, master, table_names):
        super().__init__(master)
        self.title("Перетин таблиць")
        self.result = None

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Таблиця 1:").grid(row=0, column=0, sticky="w")
        self.t1_var = tk.StringVar(value=table_names[0] if table_names else "")
        ttk.Combobox(frm, textvariable=self.t1_var, values=table_names, state="readonly", width=20).grid(
            row=0, column=1, pady=4
        )

        ttk.Label(frm, text="Таблиця 2:").grid(row=1, column=0, sticky="w")
        self.t2_var = tk.StringVar(value=table_names[-1] if table_names else "")
        ttk.Combobox(frm, textvariable=self.t2_var, values=table_names, state="readonly", width=20).grid(
            row=1, column=1, pady=4
        )

        ttk.Button(frm, text="Виконати перетин", command=self.on_submit).grid(row=2, column=0, columnspan=2, pady=10)

        self.grab_set()

    def on_submit(self):
        if self.t1_var.get() == self.t2_var.get():
            messagebox.showerror("Помилка", "Оберіть дві різні таблиці")
            return
        self.result = (self.t1_var.get(), self.t2_var.get())
        self.destroy()


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Міні-СУБД — десктоп-клієнт")
        self.geometry("900x520")

        self.db = Database("new_database")
        self.current_table: Table | None = None

        self._build_menu()
        self._build_layout()
        self._refresh_table_list()

    # ---------------- Меню ----------------

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Нова база", command=self.new_database)
        file_menu.add_command(label="Зберегти базу...", command=self.save_database)
        file_menu.add_command(label="Відкрити базу...", command=self.open_database)
        file_menu.add_separator()
        file_menu.add_command(label="Вихід", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

    # ---------------- Layout ----------------

    def _build_layout(self):
        # Ліва панель: список таблиць
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Таблиці бази:").pack(anchor="w")
        self.table_listbox = tk.Listbox(left, width=24, height=20)
        self.table_listbox.pack(fill="y", expand=True, pady=4)
        self.table_listbox.bind("<<ListboxSelect>>", self.on_select_table)

        ttk.Button(left, text="Створити таблицю", command=self.create_table).pack(fill="x", pady=2)
        ttk.Button(left, text="Знищити таблицю", command=self.drop_table).pack(fill="x", pady=2)
        ttk.Button(left, text="Перетин таблиць", command=self.do_intersect).pack(fill="x", pady=(12, 2))

        # Права панель: перегляд рядків обраної таблиці
        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(right, show="headings")
        self.tree.pack(fill="both", expand=True)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Додати рядок", command=self.add_row).pack(side="left", padx=2)
        ttk.Button(btns, text="Редагувати рядок", command=self.edit_row).pack(side="left", padx=2)
        ttk.Button(btns, text="Видалити рядок", command=self.delete_row).pack(side="left", padx=2)

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(side="bottom", fill="x")

    # ---------------- Дії з базою ----------------

    def new_database(self):
        name = simpledialog.askstring("Нова база", "Ім'я бази:", initialvalue="new_database")
        if name:
            self.db = Database(name)
            self.current_table = None
            self._refresh_table_list()
            self._refresh_tree()
            self.status_var.set(f"Створено нову базу '{name}'")

    def save_database(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.db.save(path)
            self.status_var.set(f"Базу збережено: {path}")

    def open_database(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            try:
                self.db = Database.load(path)
                self.current_table = None
                self._refresh_table_list()
                self._refresh_tree()
                self.status_var.set(f"Базу завантажено: {path}")
            except DatabaseError as e:
                messagebox.showerror("Помилка", str(e))

    # ---------------- Дії з таблицями ----------------

    def create_table(self):
        dlg = CreateTableDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            name, columns = dlg.result
            try:
                self.db.create_table(name, columns)
                self._refresh_table_list()
                self.status_var.set(f"Таблицю '{name}' створено")
            except DatabaseError as e:
                messagebox.showerror("Помилка", str(e))

    def drop_table(self):
        if not self.current_table:
            messagebox.showinfo("Інфо", "Оберіть таблицю зі списку")
            return
        if messagebox.askyesno("Підтвердження", f"Знищити таблицю '{self.current_table.name}'?"):
            self.db.drop_table(self.current_table.name)
            self.current_table = None
            self._refresh_table_list()
            self._refresh_tree()

    def do_intersect(self):
        names = self.db.list_tables()
        if len(names) < 2:
            messagebox.showinfo("Інфо", "Потрібно щонайменше 2 таблиці для перетину")
            return
        dlg = IntersectDialog(self, names)
        self.wait_window(dlg)
        if dlg.result:
            n1, n2 = dlg.result
            try:
                result = intersect(self.db.get_table(n1), self.db.get_table(n2))
                # додаємо результат як нову таблицю в базу, щоб було видно в списку
                self.db.tables[result.name] = result
                self._refresh_table_list()
                messagebox.showinfo(
                    "Готово", f"Перетин виконано: {len(result.rows)} спільних рядків. "
                    f"Результат у таблиці '{result.name}'."
                )
            except TableError as e:
                messagebox.showerror("Помилка", str(e))

    # ---------------- Дії з рядками ----------------

    def add_row(self):
        if not self.current_table:
            messagebox.showinfo("Інфо", "Оберіть таблицю зі списку")
            return
        dlg = RowDialog(self, self.current_table)
        self.wait_window(dlg)
        if dlg.result:
            try:
                self.current_table.add_row(dlg.result)
                self._refresh_tree()
            except FieldTypeError as e:
                messagebox.showerror("Помилка", str(e))

    def edit_row(self):
        sel = self.tree.selection()
        if not self.current_table or not sel:
            messagebox.showinfo("Інфо", "Оберіть рядок для редагування")
            return
        index = self.tree.index(sel[0])
        current_values = self.current_table.rows[index].values
        dlg = RowDialog(self, self.current_table, initial_values=current_values)
        self.wait_window(dlg)
        if dlg.result:
            try:
                self.current_table.edit_row(index, dlg.result)
                self._refresh_tree()
            except FieldTypeError as e:
                messagebox.showerror("Помилка", str(e))

    def delete_row(self):
        sel = self.tree.selection()
        if not self.current_table or not sel:
            return
        index = self.tree.index(sel[0])
        self.current_table.delete_row(index)
        self._refresh_tree()

    # ---------------- Оновлення відображення ----------------

    def _refresh_table_list(self):
        self.table_listbox.delete(0, tk.END)
        for name in self.db.list_tables():
            self.table_listbox.insert(tk.END, name)

    def on_select_table(self, event):
        sel = self.table_listbox.curselection()
        if not sel:
            return
        name = self.table_listbox.get(sel[0])
        self.current_table = self.db.get_table(name)
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.current_table:
            self.tree["columns"] = []
            return
        cols = self.current_table.column_names()
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120)
        for row_str in self.current_table.get_rows_as_strings():
            self.tree.insert("", tk.END, values=row_str)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
