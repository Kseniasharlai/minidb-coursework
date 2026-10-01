"""
Службовий скрипт: автоматично проходить по основних сценаріях GUI
і робить скріншоти для звіту. НЕ є частиною самого застосунку.
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desktop_app.gui import MainApp, RowDialog
from core.table import Column
from core.types import IntegerType, StringType, RealIntervalType, RealType

OUT_DIR = "/home/claude/minidb/screenshots"
os.makedirs(OUT_DIR, exist_ok=True)


def shot(name):
    path = os.path.join(OUT_DIR, name)
    subprocess.run(["import", "-window", "root", path], check=True)
    print("saved", path)


def run():
    app = MainApp()
    app.update()
    steps = iter(range(20))

    def step():
        n = next(steps, None)
        if n == 0:
            shot("01_main_window_empty.png")
            # Створюємо таблицю students програмно (як результат діалогу створення)
            app.db.create_table(
                "students",
                [
                    Column("id", IntegerType()),
                    Column("name", StringType()),
                    Column("score", RealIntervalType()),
                ],
            )
            app._refresh_table_list()
            app.table_listbox.selection_set(0)
            app.current_table = app.db.get_table("students")
            app._refresh_tree()
            app.update()
            app.after(400, step)
        elif n == 1:
            shot("02_table_created_students.png")
            app.after(200, step)
        elif n == 2:
            # Показуємо діалог додавання рядка (для скріншота форми з валідацією)
            app._demo_dialog = RowDialog(app, app.current_table)
            app.update()
            app.after(400, step)
        elif n == 3:
            shot("03_add_row_dialog.png")
            app._demo_dialog.destroy()
            # Додаємо кілька рядків напряму (як після успішного заповнення форми)
            app.current_table.add_row(["1", "Ivan", "3.0;4.5"])
            app.current_table.add_row(["2", "Olena", "4.0;5.0"])
            app.current_table.add_row(["3", "Petro", "2.0;3.5"])
            app._refresh_tree()
            app.update()
            app.after(400, step)
        elif n == 4:
            shot("04_rows_filled.png")
            # Друга таблиця з такою ж схемою для перетину
            app.db.create_table(
                "students_group_b",
                [
                    Column("id", IntegerType()),
                    Column("name", StringType()),
                    Column("score", RealIntervalType()),
                ],
            )
            t2 = app.db.get_table("students_group_b")
            t2.add_row(["2", "Olena", "4.0;5.0"])
            t2.add_row(["3", "Petro", "2.0;3.5"])
            t2.add_row(["9", "Maria", "1.0;2.0"])
            app._refresh_table_list()
            app.update()
            app.after(300, step)
        elif n == 5:
            shot("05_two_tables_ready.png")
            from desktop_app.gui import IntersectDialog
            app._demo_dialog2 = IntersectDialog(app, app.db.list_tables())
            app.update()
            app.after(400, step)
        elif n == 6:
            shot("06_intersect_dialog.png")
            app._demo_dialog2.t1_var.set("students")
            app._demo_dialog2.t2_var.set("students_group_b")
            app.update()
            app.after(300, step)
        elif n == 7:
            shot("07_intersect_dialog_selected.png")
            from core.operations import intersect
            result = intersect(
                app.db.get_table("students"), app.db.get_table("students_group_b")
            )
            app.db.tables[result.name] = result
            app._demo_dialog2.destroy()
            app._refresh_table_list()
            # обираємо результуючу таблицю в списку
            names = app.db.list_tables()
            idx = names.index(result.name)
            app.table_listbox.selection_clear(0, "end")
            app.table_listbox.selection_set(idx)
            app.current_table = app.db.get_table(result.name)
            app._refresh_tree()
            app.update()
            app.after(400, step)
        elif n == 8:
            shot("08_intersect_result.png")
            # Демонстрація збереження бази
            save_path = "/home/claude/minidb/screenshots/demo_db.json"
            app.db.save(save_path)
            app.status_var.set(f"Базу збережено: {save_path}")
            app.update()
            app.after(300, step)
        elif n == 9:
            shot("09_saved_status.png")
            app.after(200, step)
        else:
            app.destroy()

    app.after(500, step)
    app.mainloop()


if __name__ == "__main__":
    run()
