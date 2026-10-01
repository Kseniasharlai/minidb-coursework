"""Службовий скрипт: скріншоти demonstration для віддаленого GUI-клієнта."""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desktop_app.gui_remote import RemoteMainApp, RowDialog, IntersectDialog

OUT_DIR = "/home/claude/minidb/screenshots_remote"
os.makedirs(OUT_DIR, exist_ok=True)


def shot(name):
    path = os.path.join(OUT_DIR, name)
    subprocess.run(["import", "-window", "root", path], check=True)
    print("saved", path)


def run():
    app = RemoteMainApp("http://127.0.0.1:5000")
    app.update()
    steps = iter(range(20))

    def step():
        n = next(steps, None)
        if n == 0:
            app.update()
            shot("01_remote_main_connected.png")
            app.api.create_table(
                "students",
                [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "score", "type": "realInvl"},
                ],
            )
            app._refresh_table_list()
            app.table_listbox.selection_set(0)
            app.current_table_name = "students"
            app._refresh_tree()
            app.update()
            app.after(400, step)
        elif n == 1:
            shot("02_remote_table_created.png")
            app.after(200, step)
        elif n == 2:
            app._demo_dialog = RowDialog(app, app.current_table_columns)
            app.update()
            app.after(400, step)
        elif n == 3:
            shot("03_remote_add_row_dialog.png")
            app._demo_dialog.destroy()
            app.api.add_row("students", ["1", "Ivan", "3.0;4.5"])
            app.api.add_row("students", ["2", "Olena", "4.0;5.0"])
            app.api.add_row("students", ["3", "Petro", "2.0;3.5"])
            app._refresh_tree()
            app.update()
            app.after(400, step)
        elif n == 4:
            shot("04_remote_rows_filled.png")
            app.api.create_table(
                "students_group_b",
                [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "score", "type": "realInvl"},
                ],
            )
            app.api.add_row("students_group_b", ["2", "Olena", "4.0;5.0"])
            app.api.add_row("students_group_b", ["3", "Petro", "2.0;3.5"])
            app.api.add_row("students_group_b", ["9", "Maria", "1.0;2.0"])
            app._refresh_table_list()
            app.update()
            app.after(300, step)
        elif n == 5:
            shot("05_remote_two_tables.png")
            app._demo_dialog2 = IntersectDialog(app, app.api.list_tables())
            app.update()
            app.after(400, step)
        elif n == 6:
            app._demo_dialog2.t1_var.set("students")
            app._demo_dialog2.t2_var.set("students_group_b")
            app.update()
            shot("06_remote_intersect_dialog.png")
            app.after(300, step)
        elif n == 7:
            result = app.api.intersect("students", "students_group_b")
            app._demo_dialog2.destroy()
            app._refresh_table_list()
            names = app.api.list_tables()
            idx = names.index(result["result_table"])
            app.table_listbox.selection_clear(0, "end")
            app.table_listbox.selection_set(idx)
            app.current_table_name = result["result_table"]
            app._refresh_tree()
            app.update()
            app.after(400, step)
        elif n == 8:
            shot("07_remote_intersect_result.png")
            app.after(200, step)
        else:
            app.destroy()

    app.after(500, step)
    app.mainloop()


if __name__ == "__main__":
    run()
