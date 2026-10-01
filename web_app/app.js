/*
 * Веб-клієнт міні-СУБД. Уся бізнес-логіка (валідація типів, перетин таблиць)
 * виконується на сервері (server/app.py) — тут лише виклики fetch() до REST API
 * та оновлення DOM. Той самий сервер, що й для десктоп-клієнта gui_remote.py
 * (Етап 2, бонус) — підтверджує, що ядро й API повторно використані без змін.
 */

const API = "/api";

let currentTable = null;      // ім'я обраної таблиці
let currentColumns = [];      // схема обраної таблиці ([{name, type}, ...])
let selectedRowIndex = null;  // індекс обраного рядка (для edit/delete)

const el = (id) => document.getElementById(id);

function setStatus(text) {
  el("status-bar").textContent = text;
}

function showModal(id) { el(id).classList.remove("hidden"); }
function hideModal(id) { el(id).classList.add("hidden"); }

async function apiRequest(method, path, body) {
  const resp = await fetch(API + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await resp.json(); } catch (e) { /* немає тіла відповіді */ }
  if (!resp.ok) {
    const message = (data && data.error) ? data.error : `HTTP ${resp.status}`;
    throw new Error(message);
  }
  return data;
}

// ---------------------------------------------------------------------------
// Підключення / стан з'єднання
// ---------------------------------------------------------------------------

async function checkConnection() {
  const statusEl = el("connection-status");
  try {
    const info = await apiRequest("GET", "/health");
    statusEl.textContent = `Підключено · база: ${info.database}`;
    statusEl.className = "connected";
  } catch (e) {
    statusEl.textContent = "Немає з'єднання із сервером";
    statusEl.className = "error";
  }
}

// ---------------------------------------------------------------------------
// Список і перегляд таблиць
// ---------------------------------------------------------------------------

async function refreshTableList() {
  const data = await apiRequest("GET", "/tables");
  const list = el("table-list");
  list.innerHTML = "";
  data.tables.forEach((name) => {
    const li = document.createElement("li");
    li.textContent = name;
    if (name === currentTable) li.classList.add("selected");
    li.addEventListener("click", () => selectTable(name));
    list.appendChild(li);
  });
}

async function selectTable(name) {
  currentTable = name;
  selectedRowIndex = null;
  await refreshTableList();
  await refreshRows();
}

async function refreshRows() {
  const titleEl = el("current-table-title");
  const headRow = el("table-head-row");
  const body = el("table-body");
  headRow.innerHTML = "";
  body.innerHTML = "";

  if (!currentTable) {
    titleEl.textContent = "Оберіть таблицю зліва";
    return;
  }

  const data = await apiRequest("GET", `/tables/${currentTable}`);
  currentColumns = data.columns;
  titleEl.textContent = `Таблиця: ${data.name}`;

  data.columns.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = `${c.name} (${c.type})`;
    headRow.appendChild(th);
  });

  data.rows.forEach((row, idx) => {
    const tr = document.createElement("tr");
    tr.dataset.index = idx;
    row.forEach((val) => {
      const td = document.createElement("td");
      td.textContent = val;
      tr.appendChild(td);
    });
    tr.addEventListener("click", () => {
      document.querySelectorAll("#table-body tr").forEach((r) => r.classList.remove("selected"));
      tr.classList.add("selected");
      selectedRowIndex = idx;
    });
    body.appendChild(tr);
  });
}

// ---------------------------------------------------------------------------
// Створення / знищення таблиці
// ---------------------------------------------------------------------------

const TYPE_NAMES = ["integer", "real", "char", "string", "picture", "realInvl"];

function addColumnRow() {
  const container = el("columns-container");
  const row = document.createElement("div");
  row.className = "column-row";

  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.placeholder = "ім'я колонки";

  const typeSelect = document.createElement("select");
  TYPE_NAMES.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    typeSelect.appendChild(opt);
  });

  row.appendChild(nameInput);
  row.appendChild(typeSelect);
  container.appendChild(row);
}

el("btn-add-column-row").addEventListener("click", addColumnRow);

el("btn-create-table").addEventListener("click", () => {
  el("new-table-name").value = "";
  el("columns-container").innerHTML = "";
  addColumnRow();
  showModal("modal-create-table");
});

el("btn-cancel-create-table").addEventListener("click", () => hideModal("modal-create-table"));

el("btn-confirm-create-table").addEventListener("click", async () => {
  const name = el("new-table-name").value.trim();
  if (!name) { alert("Вкажіть ім'я таблиці"); return; }

  const columns = [];
  document.querySelectorAll("#columns-container .column-row").forEach((row) => {
    const cname = row.querySelector("input").value.trim();
    const ctype = row.querySelector("select").value;
    if (cname) columns.push({ name: cname, type: ctype });
  });
  if (columns.length === 0) { alert("Додайте хоча б одну колонку"); return; }

  try {
    await apiRequest("POST", "/tables", { name, columns });
    hideModal("modal-create-table");
    setStatus(`Таблицю '${name}' створено на сервері`);
    await refreshTableList();
  } catch (e) {
    alert("Помилка сервера: " + e.message);
  }
});

el("btn-drop-table").addEventListener("click", async () => {
  if (!currentTable) { alert("Оберіть таблицю зі списку"); return; }
  if (!confirm(`Знищити таблицю '${currentTable}'?`)) return;
  try {
    await apiRequest("DELETE", `/tables/${currentTable}`);
    currentTable = null;
    await refreshTableList();
    await refreshRows();
    setStatus("Таблицю знищено");
  } catch (e) {
    alert("Помилка сервера: " + e.message);
  }
});

// ---------------------------------------------------------------------------
// Рядки: додавання / редагування / видалення
// ---------------------------------------------------------------------------

function buildRowFields(initialValues) {
  const container = el("row-fields-container");
  container.innerHTML = "";
  currentColumns.forEach((col, i) => {
    const label = document.createElement("label");
    label.textContent = `${col.name} (${col.type})`;
    const input = document.createElement("input");
    input.type = "text";
    input.dataset.colIndex = i;
    input.value = initialValues ? initialValues[i] : "";
    label.appendChild(input);
    container.appendChild(label);
  });
}

el("btn-add-row").addEventListener("click", () => {
  if (!currentTable) { alert("Оберіть таблицю зі списку"); return; }
  el("row-modal-title").textContent = "Додати рядок";
  buildRowFields(null);
  el("modal-row").dataset.mode = "add";
  showModal("modal-row");
});

el("btn-edit-row").addEventListener("click", () => {
  if (!currentTable || selectedRowIndex === null) { alert("Оберіть рядок у таблиці"); return; }
  const tr = document.querySelector(`#table-body tr[data-index='${selectedRowIndex}']`);
  const values = Array.from(tr.children).map((td) => td.textContent);
  el("row-modal-title").textContent = "Редагувати рядок";
  buildRowFields(values);
  el("modal-row").dataset.mode = "edit";
  showModal("modal-row");
});

el("btn-cancel-row").addEventListener("click", () => hideModal("modal-row"));

el("btn-confirm-row").addEventListener("click", async () => {
  const inputs = document.querySelectorAll("#row-fields-container input");
  const values = Array.from(inputs).map((i) => i.value);
  const mode = el("modal-row").dataset.mode;

  try {
    if (mode === "add") {
      await apiRequest("POST", `/tables/${currentTable}/rows`, { values });
      setStatus("Рядок додано");
    } else {
      await apiRequest("PUT", `/tables/${currentTable}/rows/${selectedRowIndex}`, { values });
      setStatus("Рядок оновлено");
    }
    hideModal("modal-row");
    await refreshRows();
  } catch (e) {
    alert("Помилка валідації (від сервера): " + e.message);
  }
});

el("btn-delete-row").addEventListener("click", async () => {
  if (!currentTable || selectedRowIndex === null) { alert("Оберіть рядок у таблиці"); return; }
  try {
    await apiRequest("DELETE", `/tables/${currentTable}/rows/${selectedRowIndex}`);
    selectedRowIndex = null;
    setStatus("Рядок видалено");
    await refreshRows();
  } catch (e) {
    alert("Помилка сервера: " + e.message);
  }
});

// ---------------------------------------------------------------------------
// Перетин таблиць (індивідуальна операція варіанту)
// ---------------------------------------------------------------------------

el("btn-intersect").addEventListener("click", async () => {
  const data = await apiRequest("GET", "/tables");
  if (data.tables.length < 2) { alert("Потрібно щонайменше 2 таблиці"); return; }

  const fill = (selectId) => {
    const select = el(selectId);
    select.innerHTML = "";
    data.tables.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      select.appendChild(opt);
    });
  };
  fill("intersect-t1");
  fill("intersect-t2");
  el("intersect-t2").selectedIndex = data.tables.length - 1;

  showModal("modal-intersect");
});

el("btn-cancel-intersect").addEventListener("click", () => hideModal("modal-intersect"));

el("btn-confirm-intersect").addEventListener("click", async () => {
  const t1 = el("intersect-t1").value;
  const t2 = el("intersect-t2").value;
  if (t1 === t2) { alert("Оберіть дві різні таблиці"); return; }

  try {
    const result = await apiRequest("POST", "/intersect", { table1: t1, table2: t2 });
    hideModal("modal-intersect");
    setStatus(`Перетин виконано на сервері: ${result.row_count} спільних рядків -> '${result.result_table}'`);
    await selectTable(result.result_table);
  } catch (e) {
    alert("Помилка сервера: " + e.message);
  }
});

// ---------------------------------------------------------------------------
// Збереження / завантаження бази
// ---------------------------------------------------------------------------

el("btn-save-db").addEventListener("click", async () => {
  const path = prompt("Шлях на СЕРВЕРІ для збереження бази:", "/tmp/web_db.json");
  if (!path) return;
  try {
    await apiRequest("POST", "/database/save", { path });
    setStatus(`Базу збережено на сервері: ${path}`);
  } catch (e) {
    alert("Помилка сервера: " + e.message);
  }
});

el("btn-load-db").addEventListener("click", async () => {
  const path = prompt("Шлях на СЕРВЕРІ для завантаження бази:", "/tmp/web_db.json");
  if (!path) return;
  try {
    await apiRequest("POST", "/database/load", { path });
    currentTable = null;
    setStatus(`Базу завантажено з сервера: ${path}`);
    await refreshTableList();
    await refreshRows();
  } catch (e) {
    alert("Помилка сервера: " + e.message);
  }
});

// ---------------------------------------------------------------------------
// Ініціалізація
// ---------------------------------------------------------------------------

(async function init() {
  await checkConnection();
  await refreshTableList();
  await refreshRows();

  // Службовий хук лише для автоматичних скріншотів звіту (?demoModal=create-table
  // або ?demoModal=intersect) — відкриває модальне вікно одразу після завантаження
  // сторінки, без потреби емулювати клік мишею. На реальну роботу застосунку
  // не впливає.
  const params = new URLSearchParams(window.location.search);
  const demoModal = params.get("demoModal");
  if (demoModal === "create-table") {
    el("columns-container").innerHTML = "";
    addColumnRow();
    addColumnRow();
    addColumnRow();
    showModal("modal-create-table");
  } else if (demoModal === "intersect") {
    const data = await apiRequest("GET", "/tables");
    const fill = (selectId) => {
      const select = el(selectId);
      select.innerHTML = "";
      data.tables.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      });
    };
    fill("intersect-t1");
    fill("intersect-t2");
    el("intersect-t2").selectedIndex = data.tables.length - 1;
    showModal("modal-intersect");
  } else if (demoModal === "add-row") {
    el("row-modal-title").textContent = "Додати рядок";
    buildRowFields(null);
    el("modal-row").dataset.mode = "add";
    showModal("modal-row");
  }
})();
