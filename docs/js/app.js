// Static demo of the service request dashboard. Runs fully in the browser:
// demo data comes from data/*.json, new requests are kept in localStorage.
(async function () {
  const [cfg, tr, demo] = await Promise.all(
    ["data/categories.json", "data/translations.json", "data/demo.json"]
      .map((url) => fetch(url).then((r) => r.json())));

  const LS_REQUESTS = "csrm_requests";
  const LS_LANG = "csrm_lang";
  const SS_PHONE = "csrm_phone";
  const MAX_DESCRIPTION = 1000;

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

  // ---- data ----------------------------------------------------------------
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

  function myRequests() {
    return allRequests()
      .filter((r) => r.phone === phoneOf())
      .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
  }

  function addRequest(category, subcategory, description) {
    const all = allRequests();
    const stamp = new Date().toISOString().replace(/\.\d+Z$/, "Z");
    const created = {
      id: Math.max(0, ...all.map((r) => r.id)) + 1, phone: phoneOf(), category, subcategory,
      description, status: "open", created_at: stamp, updated_at: stamp,
      history: [{ status: "open", changed_at: stamp }],
    };
    localStorage.setItem(LS_REQUESTS, JSON.stringify(userRequests().concat(created)));
  }

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
      if (/^\d{9,15}$/.test(digits)) {
        sessionStorage.setItem(SS_PHONE, digits);
        location.hash = "#/dashboard";
      } else {
        loginView("invalid_phone");
      }
    });
  }

  function dashboardView() {
    const rows = myRequests();
    const notice = state.flash ? `<div class="notice">${t(state.flash)}</div>` : "";
    state.flash = null;
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
      <div class="footer-actions">
        <button type="button" class="btn btn-secondary" id="reset">${t("reset_demo")}</button>
      </div>`;
    document.getElementById("logout").addEventListener("click", () => {
      sessionStorage.removeItem(SS_PHONE);
      location.hash = "#/login";
    });
    document.getElementById("reset").addEventListener("click", () => {
      localStorage.removeItem(LS_REQUESTS);
      dashboardView();
    });
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
    document.getElementById("new-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const values = {
        category: catSel.value, subcategory: subSel.value,
        description: document.getElementById("description").value.trim(),
      };
      const valid = cats[values.category]?.subcategories.some((s) => s.id === values.subcategory);
      if (!valid) return newRequestView("invalid_category", values);
      if (values.description.length > MAX_DESCRIPTION) return newRequestView("description_too_long", values);
      addRequest(values.category, values.subcategory, values.description);
      state.flash = "request_created";
      location.hash = "#/dashboard";
    });
  }

  function detailView(id) {
    const r = myRequests().find((x) => x.id === id);
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
        <h2>${t("status_history")}</h2>
        <ol class="timeline">${r.history.map((h) =>
          `<li>${statusBadge(h.status)}<span class="when">${fmtDate(h.changed_at)}</span></li>`).join("")}</ol>
        <a class="btn btn-secondary" href="#/dashboard">${t("back")}</a>
      </section>`;
  }

  // ---- routing -------------------------------------------------------------
  function render() {
    document.documentElement.lang = state.lang;
    document.documentElement.dir = state.lang === "he" ? "rtl" : "ltr";
    document.title = t("app_title");
    document.getElementById("app-title").textContent = t("app_title");
    document.getElementById("banner").textContent = t("static_banner");
    document.querySelectorAll("[data-lang]").forEach((a) =>
      a.classList.toggle("active", a.dataset.lang === state.lang));

    const route = location.hash.replace(/^#\/?/, "");
    if (!phoneOf() || route === "login") return loginView();
    if (route === "new") return newRequestView();
    const match = route.match(/^request\/(\d+)$/);
    if (match) return detailView(Number(match[1]));
    return dashboardView();
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
