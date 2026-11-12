// Static demo of the service request dashboard. Runs fully in the browser.
// Data source: built-in demo data + localStorage (default), or an Airtable Base when connected.
// The Airtable token is kept in this browser's localStorage only. It is never stored in the repo.
(async function () {
  const [cfg, tr, demo] = await Promise.all(
    ["data/categories.json", "data/translations.json", "data/demo.json"]
      .map((url) => fetch(url).then((r) => r.json())));

  const LS_REQUESTS = "csrm_requests";
  const LS_LANG = "csrm_lang";
  const LS_AIRTABLE = "csrm_airtable";
  const SS_PHONE = "csrm_phone";
  const SS_ADMIN = "csrm_admin";
  const MAX_DESCRIPTION = 1000;
  const TOKEN_RE = /^[A-Za-z0-9._-]{20,300}$/;
  const BASE_RE = /^app[A-Za-z0-9]{10,20}$/;
  const AT_API = "https://api.airtable.com/v0";
  const AT_TABLE = "Requests";

  const state = {
    lang: localStorage.getItem(LS_LANG) === "he" ? "he" : "en",
    flash: null,
  };
  const cats = Object.fromEntries(cfg.categories.map((c) => [c.id, c]));
  const stats = Object.fromEntries(cfg.statuses.map((s) => [s.id, s]));
  const app = document.getElementById("app");

  const t = (key) => tr[state.lang][key] ?? key;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---- Airtable connection (stored in this browser only) --------------------
  // A link like  .../#airtable=<token>,<baseId>  connects the visitor's browser, then the
  // token is removed from the address bar. The fragment is never sent to any server.
  (function importFromLink() {
    const m = location.hash.match(/^#airtable=([^,&]+),(app[A-Za-z0-9]+)$/);
    if (!m) return;
    history.replaceState(null, "", location.pathname + location.search + "#/login");
    if (TOKEN_RE.test(m[1]) && BASE_RE.test(m[2])) {
      localStorage.setItem(LS_AIRTABLE, JSON.stringify({ token: m[1], base: m[2] }));
    }
  })();

  function airtableConf() {
    try {
      const conf = JSON.parse(localStorage.getItem(LS_AIRTABLE) || "null");
      return conf && TOKEN_RE.test(conf.token) && BASE_RE.test(conf.base) ? conf : null;
    } catch (e) {
      return null;
    }
  }

  class AirtableError extends Error {
    constructor(status, kind) {
      super(`${status} ${kind}`.trim());
      this.status = status;
      this.kind = kind;
    }
  }

  async function atFetch(conf, path, options = {}) {
    const url = `${AT_API}/${conf.base}/${AT_TABLE}${path}`;
    const init = {
      ...options,
      headers: { Authorization: `Bearer ${conf.token}`, "Content-Type": "application/json" },
    };
    for (let attempt = 0; attempt < 3; attempt++) {
      let res;
      try {
        res = await fetch(url, init);
      } catch (e) {
        throw new AirtableError(0, "NETWORK");
      }
      if (res.status === 429 && attempt < 2) {  // rate limit: 5 requests/second/base
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      if (!res.ok) {
        let kind = "";
        try {
          const body = await res.json();
          kind = typeof body.error === "string" ? body.error : (body.error && body.error.type) || "";
        } catch (e) { /* no JSON body */ }
        throw new AirtableError(res.status, String(kind).replace(/[^A-Za-z0-9_ ]/g, "").slice(0, 60));
      }
      return res.json();
    }
  }

  const formulaStr = (value) =>
    "'" + String(value).replace(/[\u0000-\u001f]/g, "").replace(/\\/g, "\\\\").replace(/'/g, "\\'") + "'";

  async function atList(conf, formula) {
    const records = [];
    let offset;
    for (let page = 0; page < 20; page++) {  // at most 2000 records
      const params = new URLSearchParams({
        filterByFormula: formula, pageSize: "100",
        "sort[0][field]": "RequestID", "sort[0][direction]": "desc",
      });
      if (offset) params.set("offset", offset);
      const res = await atFetch(conf, `?${params}`);
      records.push(...res.records);
      offset = res.offset;
      if (!offset) break;
    }
    return records;
  }

  const byEnglishName = (items) => Object.fromEntries(items.map((i) => [i.en, i.id]));
  const allSubs = cfg.categories.flatMap((c) => c.subcategories);
  const catByName = byEnglishName(cfg.categories);
  const subByName = byEnglishName(allSubs);
  const statusByName = byEnglishName(cfg.statuses);
  const nameById = Object.fromEntries(
    [...cfg.categories, ...allSubs, ...cfg.statuses].map((i) => [i.id, i.en]));
  const cleanIso = (v) => (typeof v === "string" ? v.replace(/\.\d+Z$/, "Z") : "");

  function recordToRow(rec) {
    const f = rec.fields || {};
    if (!Number.isInteger(f.RequestID)) return null;
    const created = cleanIso(rec.createdTime);
    return {
      id: f.RequestID, phone: f.Phone || "",
      category: catByName[f.Category] ?? f.Category ?? "",
      subcategory: subByName[f.Subcategory] ?? f.Subcategory ?? "",
      description: f.Description || "",
      status: statusByName[f.Status] ?? f.Status ?? "",
      created_at: created, updated_at: cleanIso(f.Updated) || created,
      history: null,  // Airtable keeps only the current status
    };
  }

  // ---- data sources ---------------------------------------------------------
  const now = Date.now();
  const isoDaysAgo = (days) =>
    new Date(now - days * 86400000).toISOString().replace(/\.\d+Z$/, "Z");

  const demoRequests = demo.requests.map((r, i) => {
    const history = r.history.map(([status, days]) => ({ status, changed_at: isoDaysAgo(days) }));
    return {
      id: i + 1, phone: r.phone, category: r.category, subcategory: r.subcategory,
      description: r.description, status: history[history.length - 1].status,
      created_at: history[0].changed_at,
      updated_at: history[history.length - 1].changed_at, history,
    };
  });

  const userRequests = () => JSON.parse(localStorage.getItem(LS_REQUESTS) || "[]");
  const allRequests = () => demoRequests.concat(userRequests());
  const phoneOf = () => sessionStorage.getItem(SS_PHONE);
  const isAdmin = () => sessionStorage.getItem(SS_ADMIN) === "1";

  const staticSource = {
    name: "static",
    async list(phone) {
      return allRequests().filter((r) => r.phone === phone)
        .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
    },
    async get(id, phone) {
      return allRequests().find((r) => r.id === id && r.phone === phone) || null;
    },
    async create(phone, category, subcategory, description) {
      const stamp = new Date().toISOString().replace(/\.\d+Z$/, "Z");
      const id = Math.max(0, ...allRequests().map((r) => r.id)) + 1;
      localStorage.setItem(LS_REQUESTS, JSON.stringify(userRequests().concat({
        id, phone, category, subcategory, description, status: "open",
        created_at: stamp, updated_at: stamp, history: [{ status: "open", changed_at: stamp }],
      })));
    },
  };

  const airtableSource = (conf) => ({
    name: "airtable",
    async list(phone) {
      const records = await atList(conf, `{Phone}=${formulaStr(phone)}`);
      return records.map(recordToRow).filter(Boolean);
    },
    async get(id, phone) {
      const records = await atList(
        conf, `AND({Phone}=${formulaStr(phone)},{RequestID}=${Number(id)})`);
      return records.map(recordToRow).filter(Boolean)[0] || null;
    },
    async create(phone, category, subcategory, description) {
      await atFetch(conf, "", {
        method: "POST",
        body: JSON.stringify({ fields: {
          Phone: phone, Category: nameById[category], Subcategory: nameById[subcategory],
          Description: description, Status: nameById.open } }),
      });
    },
  });

  const source = () => {
    const conf = airtableConf();
    return conf ? airtableSource(conf) : staticSource;
  };

  // ---- formatting helpers ---------------------------------------------------
  const name = (item) => item[state.lang];
  const categoryName = (id) => (cats[id] ? name(cats[id]) : id);
  const subName = (cid, sid) => {
    const sub = cats[cid]?.subcategories.find((s) => s.id === sid);
    return sub ? name(sub) : sid;
  };
  const statusBadge = (id) => {
    const s = stats[id];
    return `<span class="badge" style="background: ${s ? s.color : "#d9d9d9"}">${esc(s ? name(s) : id)}</span>`;
  };
  const pad = (n) => String(n).padStart(2, "0");
  const fmtDate = (iso) => {
    const d = new Date(iso);
    const text = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    return `<bdi dir="ltr">${text}</bdi>`;
  };
  const requestNo = (id) => `SR-${String(id).padStart(4, "0")}`;
  const maskToken = (token) => `${token.slice(0, 3)}…${token.slice(-4)}`;

  function takeFlash() {
    const html = state.flash ? `<div class="notice">${t(state.flash)}</div>` : "";
    state.flash = null;
    return html;
  }

  function errorView(err) {
    const detail = err instanceof AirtableError ? ` <bdi dir="ltr">(${esc(err.message)})</bdi>` : "";
    app.innerHTML = `<section class="card narrow"><p class="error">${t("service_error")}${detail}</p>
      <a class="btn" href="#/dashboard">${t("back")}</a></section>`;
  }

  // ---- views ---------------------------------------------------------------
  function loginView(error) {
    app.innerHTML = `
      <section class="card narrow">
        <h1>${t("login_title")}</h1>
        <p>${t("login_prompt")}</p>
        ${error ? `<div class="error">${t(error)}</div>` : ""}
        <form id="login-form">
          <label for="phone">${t("phone")}</label>
          <input id="phone" name="phone" type="tel" inputmode="tel" required autofocus
                 dir="ltr" placeholder="${esc(t("phone_placeholder"))}">
          <button type="submit" class="btn">${t("continue")}</button>
        </form>
        <div class="demo">
          <p>${t("demo_phones")}</p>
          <ul>${demo.phones.map((p) =>
            `<li><button type="button" class="chip" data-phone="${p}" dir="ltr">${p}</button></li>`).join("")}</ul>
        </div>
      </section>`;
    const input = document.getElementById("phone");
    app.querySelectorAll(".chip").forEach((chip) =>
      chip.addEventListener("click", () => { input.value = chip.dataset.phone; input.focus(); }));
    document.getElementById("login-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const digits = input.value.replace(/[\s\-()+]/g, "");
      if (digits === demo.admin_phone) {
        sessionStorage.removeItem(SS_PHONE);
        sessionStorage.setItem(SS_ADMIN, "1");
        location.hash = "#/admin";
      } else if (/^\d{9,15}$/.test(digits)) {
        sessionStorage.removeItem(SS_ADMIN);
        sessionStorage.setItem(SS_PHONE, digits);
        location.hash = "#/dashboard";
      } else {
        loginView("invalid_phone");
      }
    });
  }

  async function dashboardView(current) {
    app.innerHTML = `<p class="empty">${t("loading")}</p>`;
    let rows;
    try {
      rows = await source().list(phoneOf());
    } catch (err) {
      return current() && errorView(err);
    }
    if (!current()) return;
    const notice = takeFlash();
    const demoMode = !airtableConf();
    app.innerHTML = `
      ${notice}
      <div class="toolbar">
        <h1>${t("my_requests")}</h1>
        <div class="who">${t("signed_in_as")}: <bdi dir="ltr">${esc(phoneOf())}</bdi></div>
        <div class="toolbar-actions">
          <a class="btn" href="#/new">+ ${t("new_request")}</a>
          <button type="button" class="btn btn-secondary" id="logout">${t("logout")}</button>
        </div>
      </div>
      <section class="card table-wrap">
        ${rows.length ? `
        <table>
          <thead><tr>
            <th>${t("request_no")}</th><th>${t("opened")}</th><th>${t("category")}</th>
            <th>${t("subcategory")}</th><th>${t("status")}</th><th>${t("last_update")}</th>
          </tr></thead>
          <tbody>${rows.map((r) => `
            <tr class="clickable" data-href="#/request/${r.id}">
              <td data-label="${t("request_no")}"><a href="#/request/${r.id}">${requestNo(r.id)}</a></td>
              <td data-label="${t("opened")}">${fmtDate(r.created_at)}</td>
              <td data-label="${t("category")}">${esc(categoryName(r.category))}</td>
              <td data-label="${t("subcategory")}">${esc(subName(r.category, r.subcategory))}</td>
              <td data-label="${t("status")}">${statusBadge(r.status)}</td>
              <td data-label="${t("last_update")}">${fmtDate(r.updated_at)}</td>
            </tr>`).join("")}
          </tbody>
        </table>` : `<p class="empty">${t("no_requests")}</p>`}
      </section>
      ${demoMode ? `<div class="footer-actions">
        <button type="button" class="btn btn-secondary" id="reset">${t("reset_demo")}</button>
      </div>` : ""}`;
    document.getElementById("logout").addEventListener("click", () => {
      sessionStorage.removeItem(SS_PHONE);
      location.hash = "#/login";
    });
    const reset = document.getElementById("reset");
    if (reset) {
      reset.addEventListener("click", () => {
        localStorage.removeItem(LS_REQUESTS);
        render();
      });
    }
    app.querySelectorAll("tr.clickable").forEach((row) =>
      row.addEventListener("click", (e) => {
        if (!e.target.closest("a")) location.hash = row.dataset.href;
      }));
  }

  function newRequestView(error, form = { category: "", subcategory: "", description: "" }) {
    app.innerHTML = `
      <section class="card narrow">
        <h1>${t("new_request")}</h1>
        ${error ? `<div class="error">${t(error)}</div>` : ""}
        <form id="new-form">
          <label for="category">${t("category")}</label>
          <select id="category" required>
            <option value="">${t("select_category")}</option>
            ${cfg.categories.map((c) =>
              `<option value="${c.id}" ${c.id === form.category ? "selected" : ""}>${esc(name(c))}</option>`).join("")}
          </select>
          <label for="subcategory">${t("subcategory")}</label>
          <select id="subcategory" required></select>
          <label for="description">${t("description_optional")}</label>
          <textarea id="description" rows="6" maxlength="${MAX_DESCRIPTION}">${esc(form.description)}</textarea>
          <div class="form-actions">
            <button type="submit" class="btn">${t("submit")}</button>
            <a class="btn btn-secondary" href="#/dashboard">${t("cancel")}</a>
          </div>
        </form>
      </section>`;
    const catSel = document.getElementById("category");
    const subSel = document.getElementById("subcategory");
    const fillSubs = (selected) => {
      subSel.replaceChildren(new Option(t("select_subcategory"), ""));
      (cats[catSel.value]?.subcategories || []).forEach((s) =>
        subSel.add(new Option(name(s), s.id, false, s.id === selected)));
    };
    catSel.addEventListener("change", () => fillSubs(""));
    fillSubs(form.subcategory);
    document.getElementById("new-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const values = {
        category: catSel.value, subcategory: subSel.value,
        description: document.getElementById("description").value.trim(),
      };
      const valid = cats[values.category]?.subcategories.some((s) => s.id === values.subcategory);
      if (!valid) return newRequestView("invalid_category", values);
      if (values.description.length > MAX_DESCRIPTION) return newRequestView("description_too_long", values);
      try {
        await source().create(phoneOf(), values.category, values.subcategory, values.description);
      } catch (err) {
        return errorView(err);
      }
      state.flash = "request_created";
      location.hash = "#/dashboard";
    });
  }

  async function detailView(id, current) {
    app.innerHTML = `<p class="empty">${t("loading")}</p>`;
    let r;
    try {
      r = await source().get(id, phoneOf());
    } catch (err) {
      return current() && errorView(err);
    }
    if (!current()) return;
    if (!r) {
      app.innerHTML = `<section class="card narrow"><p class="error">${t("not_found")}</p>
        <a class="btn" href="#/dashboard">${t("back")}</a></section>`;
      return;
    }
    app.innerHTML = `
      <section class="card narrow">
        <h1>${requestNo(r.id)}</h1>
        <dl class="details">
          <dt>${t("status")}</dt><dd>${statusBadge(r.status)}</dd>
          <dt>${t("category")}</dt><dd>${esc(categoryName(r.category))}</dd>
          <dt>${t("subcategory")}</dt><dd>${esc(subName(r.category, r.subcategory))}</dd>
          <dt>${t("opened")}</dt><dd>${fmtDate(r.created_at)}</dd>
          <dt>${t("last_update")}</dt><dd>${fmtDate(r.updated_at)}</dd>
          <dt>${t("description")}</dt>
          <dd class="description">${r.description ? esc(r.description) : t("no_description")}</dd>
        </dl>
        ${r.history ? `<h2>${t("status_history")}</h2>
        <ol class="timeline">${r.history.map((h) =>
          `<li>${statusBadge(h.status)}<span class="when">${fmtDate(h.changed_at)}</span></li>`).join("")}</ol>` : ""}
        <a class="btn btn-secondary" href="#/dashboard">${t("back")}</a>
      </section>`;
  }

  function adminView(error, errorDetail, form = {}) {
    const conf = airtableConf();
    app.innerHTML = `
      <section class="card narrow">
        ${takeFlash()}
        <h1>${t("admin_title")}</h1>
        <p>${t("current_source")}: <b>${conf ? t("source_airtable") : t("source_static")}</b></p>
        ${error ? `<div class="error">${t(error)}${errorDetail ? ` <bdi dir="ltr">(${esc(errorDetail)})</bdi>` : ""}</div>` : ""}
        ${conf ? `
        <dl class="details">
          <dt>${t("token")}</dt><dd><bdi dir="ltr">${esc(maskToken(conf.token))}</bdi></dd>
          <dt>${t("base_id")}</dt><dd><bdi dir="ltr">${esc(conf.base)}</bdi></dd>
        </dl>
        <button type="button" class="btn" id="make-link">${t("teacher_link")}</button>
        <div id="link-box" hidden>
          <p>${t("teacher_link_note")}</p>
          <input id="link" type="text" readonly dir="ltr">
          <button type="button" class="btn btn-secondary" id="copy-link">${t("copy_link")}</button>
        </div>
        <button type="button" class="btn btn-secondary" id="disconnect">${t("disconnect")}</button>
        ` : `
        <p>${t("static_admin_intro")}</p>
        <form id="connect-form" autocomplete="off">
          <label for="token">${t("token")}</label>
          <input id="token" type="password" required dir="ltr" autocomplete="off">
          <small>${t("static_token_hint")}</small>
          <label for="base">${t("base_id")}</label>
          <input id="base" type="text" required dir="ltr" placeholder="appXXXXXXXXXXXXXX"
                 value="${esc(form.base || "")}">
          <small>${t("base_hint")}</small>
          <button type="submit" class="btn">${t("connect_static")}</button>
        </form>`}
        <button type="button" class="btn btn-secondary" id="admin-logout">${t("logout")}</button>
      </section>`;

    document.getElementById("admin-logout").addEventListener("click", () => {
      sessionStorage.removeItem(SS_ADMIN);
      location.hash = "#/login";
    });
    const connectForm = document.getElementById("connect-form");
    if (connectForm) {
      connectForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const token = document.getElementById("token").value.trim();
        const base = document.getElementById("base").value.trim();
        if (!TOKEN_RE.test(token)) return adminView("invalid_token", "", { base });
        if (!BASE_RE.test(base)) return adminView("invalid_base", "", { base });
        try {
          await atFetch({ token, base }, "?maxRecords=1");  // checks token, Base and table
        } catch (err) {
          return adminView("connect_failed", err.message, { base });
        }
        localStorage.setItem(LS_AIRTABLE, JSON.stringify({ token, base }));
        state.flash = "static_connected";
        render();
      });
    }
    const makeLink = document.getElementById("make-link");
    if (makeLink) {
      makeLink.addEventListener("click", () => {
        const link = `${location.origin}${location.pathname}#airtable=${conf.token},${conf.base}`;
        document.getElementById("link").value = link;
        document.getElementById("link-box").hidden = false;
      });
      document.getElementById("copy-link").addEventListener("click", async (e) => {
        const input = document.getElementById("link");
        input.select();
        try { await navigator.clipboard.writeText(input.value); } catch (err) { /* selected for manual copy */ }
        e.target.textContent = t("copied");
      });
      document.getElementById("disconnect").addEventListener("click", () => {
        localStorage.removeItem(LS_AIRTABLE);
        state.flash = "static_disconnected";
        render();
      });
    }
  }

  // ---- routing -------------------------------------------------------------
  let renderCount = 0;
  function render() {
    const mine = ++renderCount;
    const current = () => mine === renderCount;
    const conf = airtableConf();
    document.documentElement.lang = state.lang;
    document.documentElement.dir = state.lang === "he" ? "rtl" : "ltr";
    document.title = t("app_title");
    document.getElementById("app-title").textContent = t("app_title");
    document.getElementById("banner").textContent = t(conf ? "airtable_banner" : "static_banner");
    document.querySelectorAll("[data-lang]").forEach((a) =>
      a.classList.toggle("active", a.dataset.lang === state.lang));

    const route = location.hash.replace(/^#\/?/, "");
    if (route === "admin") return isAdmin() ? adminView() : loginView();
    if (route === "login") return loginView();
    if (!phoneOf()) return isAdmin() ? adminView() : loginView();
    if (route === "new") return newRequestView();
    const match = route.match(/^request\/(\d+)$/);
    if (match) return detailView(Number(match[1]), current);
    return dashboardView(current);
  }

  document.querySelectorAll("[data-lang]").forEach((a) =>
    a.addEventListener("click", (e) => {
      e.preventDefault();
      state.lang = a.dataset.lang;
      localStorage.setItem(LS_LANG, state.lang);
      render();
    }));
  window.addEventListener("hashchange", render);
  render();
})();
