/**
 * Precise-location store picker: sido → sigungu → dong combobox + Kakao place search.
 */

/**
 * @param {HTMLElement} host
 * @param {{
 *   getStoreType: () => string,
 *   onAddressSelected: (payload: {
 *     address: string,
 *     name: string,
 *     dongLabel?: string,
 *   }) => void,
 * }} options
 */
export function mountStorePicker(host, options) {
  host.innerHTML = "";
  host.classList.add("store-picker");
  host.hidden = true;

  const regionRow = document.createElement("div");
  regionRow.className = "store-picker-regions";

  const sidoSel = makeSelect("region-sido", "시·도 선택");
  const sigunguSel = makeSelect("region-sigungu", "시·군·구 선택");
  sigunguSel.disabled = true;

  // Dong: combobox (input + listbox) — native <select> was empty/hard to use.
  const dongField = document.createElement("div");
  dongField.className = "store-picker-region-field store-picker-dong-field";
  const dongTitle = document.createElement("span");
  dongTitle.className = "field-title";
  dongTitle.textContent = "읍·면·동·리";
  const dongCombo = document.createElement("div");
  dongCombo.className = "store-picker-dong-combo";
  const dongInput = document.createElement("input");
  dongInput.type = "text";
  dongInput.className = "store-picker-select store-picker-dong-input";
  dongInput.id = "region-dong";
  dongInput.placeholder = "시·군·구 선택 후 검색·선택";
  dongInput.autocomplete = "off";
  dongInput.disabled = true;
  dongInput.setAttribute("aria-autocomplete", "list");
  dongInput.setAttribute("aria-controls", "dong-picker-listbox");
  const dongList = document.createElement("ul");
  dongList.id = "dong-picker-listbox";
  dongList.className = "store-picker-listbox store-picker-dong-listbox";
  dongList.hidden = true;
  dongList.setAttribute("role", "listbox");
  dongCombo.appendChild(dongInput);
  dongCombo.appendChild(dongList);
  dongField.appendChild(dongTitle);
  dongField.appendChild(dongCombo);

  regionRow.appendChild(wrapField("시·도", sidoSel));
  regionRow.appendChild(wrapField("시·군·구", sigunguSel));
  regionRow.appendChild(dongField);

  const searchWrap = document.createElement("div");
  searchWrap.className = "store-picker-search";

  const searchLabel = document.createElement("span");
  searchLabel.className = "field-title";
  searchLabel.textContent = "점포명 · 도로명 · 지번 검색";

  const searchHint = document.createElement("small");
  searchHint.className = "field-hint";
  searchHint.textContent =
    "예: GS25 뉴서강대학사점 또는 백범로 35 — 자동완성에서 공식 점포를 선택하세요.";

  const input = document.createElement("input");
  input.type = "search";
  input.className = "store-picker-input";
  input.name = "store_address";
  input.id = "field-store_address";
  input.autocomplete = "off";
  input.placeholder = "점포명 또는 주소 일부";
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-controls", "store-picker-listbox");

  const listbox = document.createElement("ul");
  listbox.id = "store-picker-listbox";
  listbox.className = "store-picker-listbox";
  listbox.hidden = true;
  listbox.setAttribute("role", "listbox");

  const status = document.createElement("p");
  status.className = "store-picker-status mute";
  status.setAttribute("aria-live", "polite");

  const selected = document.createElement("div");
  selected.className = "store-picker-selected";
  selected.hidden = true;

  searchWrap.appendChild(searchLabel);
  searchWrap.appendChild(searchHint);
  searchWrap.appendChild(input);
  searchWrap.appendChild(listbox);
  searchWrap.appendChild(status);
  searchWrap.appendChild(selected);

  host.appendChild(regionRow);
  host.appendChild(searchWrap);

  /** @type {Array<object>} */
  let currentResults = [];
  /** @type {string[]} */
  let dongResults = [];
  let debounceTimer = 0;
  let dongDebounce = 0;
  let activeIndex = -1;
  let dongActive = -1;
  /** last resolved admin label for location_dong when precise */
  let lastDongLabel = "";

  async function loadSido() {
    try {
      const res = await fetch("/api/regions/sido");
      const data = await res.json();
      fillSelect(sidoSel, data.items || [], "시·도 선택");
    } catch {
      status.textContent = "시·도 목록을 불러오지 못했습니다.";
    }
  }

  async function loadSigungu() {
    const sido = sidoSel.value;
    fillSelect(sigunguSel, [], "시·군·구 선택");
    dongInput.value = "";
    dongResults = [];
    hideDongList();
    dongInput.disabled = true;
    sigunguSel.disabled = !sido;
    lastDongLabel = "";
    if (!sido) return;
    try {
      const res = await fetch(
        `/api/regions/sigungu?sido=${encodeURIComponent(sido)}`,
      );
      const data = await res.json();
      fillSelect(sigunguSel, data.items || [], "시·군·구 선택");
      sigunguSel.disabled = false;
    } catch {
      status.textContent = "시·군·구 목록을 불러오지 못했습니다.";
    }
  }

  async function loadDong(q = "") {
    const sido = sidoSel.value;
    const sigungu = sigunguSel.value;
    dongInput.disabled = !(sido && sigungu);
    if (!sido || !sigungu) {
      dongResults = [];
      hideDongList();
      return;
    }
    try {
      const params = new URLSearchParams({ sido, sigungu, q });
      const res = await fetch(`/api/regions/dong?${params}`);
      const data = await res.json();
      dongResults = (data.results || []).map((r) => r.name).filter(Boolean);
      renderDongList(dongResults);
      if (!dongResults.length) {
        status.textContent =
          (data.notes && data.notes[0]) ||
          "읍·면·동 후보가 없습니다. 직접 입력하거나 점포 검색을 이용하세요.";
      } else {
        status.textContent = `읍·면·동 ${dongResults.length}건 · 목록에서 고르거나 직접 입력`;
      }
    } catch {
      dongResults = [];
      hideDongList();
      status.textContent =
        "읍·면·동 검색에 실패했습니다. 직접 입력하거나 점포 검색을 이용하세요.";
    }
  }

  function renderDongList(items) {
    dongList.innerHTML = "";
    dongActive = -1;
    if (!items.length) {
      dongList.hidden = true;
      return;
    }
    for (let i = 0; i < items.length; i++) {
      const name = items[i];
      const li = document.createElement("li");
      li.className = "store-picker-option";
      li.setAttribute("role", "option");
      li.innerHTML = `<span class="sp-name">${escapeHtml(name)}</span>`;
      li.addEventListener("mousedown", (ev) => {
        ev.preventDefault();
        selectDong(name);
      });
      dongList.appendChild(li);
    }
    dongList.hidden = false;
  }

  function selectDong(name) {
    dongInput.value = name;
    lastDongLabel = [sidoSel.value, sigunguSel.value, name].filter(Boolean).join(" ");
    hideDongList();
    status.textContent = `지역: ${lastDongLabel}`;
    scheduleSearch();
  }

  function hideDongList() {
    dongList.hidden = true;
    dongActive = -1;
  }

  async function runSearch() {
    const q = input.value.trim();
    const sido = sidoSel.value;
    const sigungu = sigunguSel.value;
    const dong = dongInput.value.trim();
    if (q.length < 1 && !sido) {
      hideList();
      status.textContent = "지역을 고르거나 검색어를 입력하세요.";
      return;
    }
    status.textContent = "검색 중…";
    const params = new URLSearchParams({
      q,
      sido,
      sigungu,
      dong,
      store_type: options.getStoreType() || "",
    });
    try {
      const res = await fetch(`/api/places/search?${params}`);
      const data = await res.json();
      currentResults = data.results || [];
      renderList(currentResults);
      if (!currentResults.length) {
        status.textContent =
          (data.notes && data.notes[0]) || "검색 결과가 없습니다.";
      } else {
        status.textContent = `${currentResults.length}건 · 목록에서 점포를 선택하세요.`;
      }
    } catch (err) {
      hideList();
      status.textContent = `검색 실패: ${err}`;
    }
  }

  function renderList(items) {
    listbox.innerHTML = "";
    activeIndex = -1;
    if (!items.length) {
      listbox.hidden = true;
      return;
    }
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const li = document.createElement("li");
      li.className = "store-picker-option";
      li.setAttribute("role", "option");
      li.dataset.index = String(i);
      li.innerHTML = `
        <span class="sp-name">${escapeHtml(item.name)}</span>
        <span class="sp-addr">${escapeHtml(item.address_display || item.road_address || "")}</span>
        <span class="sp-meta">${escapeHtml(item.category_name || item.source || "")}</span>
      `;
      li.addEventListener("mousedown", (ev) => {
        ev.preventDefault();
        selectIndex(i);
      });
      listbox.appendChild(li);
    }
    listbox.hidden = false;
  }

  function selectIndex(i) {
    const item = currentResults[i];
    if (!item) return;
    const address = item.road_address || item.jibun_address || item.address_display;
    input.value = address;
    selected.hidden = false;
    selected.innerHTML = `
      <strong>선택 점포</strong>
      <span>${escapeHtml(item.name)}</span>
      <span class="mute">${escapeHtml(address)}</span>
    `;
    hideList();
    status.textContent = "점포가 선택되었습니다. 이 주소로 분석을 진행합니다.";
    let dongLabel = dongInput.value.trim()
      ? [sidoSel.value, sigunguSel.value, dongInput.value.trim()].filter(Boolean).join(" ")
      : "";
    if (!dongLabel && item.jibun_address) {
      const parts = String(item.jibun_address).split(/\s+/);
      if (parts.length >= 3) dongLabel = parts.slice(0, 3).join(" ");
    }
    if (!dongLabel) {
      dongLabel = [sidoSel.value, sigunguSel.value].filter(Boolean).join(" ");
    }
    lastDongLabel = dongLabel;
    // Sync dong input from jibun if empty
    if (!dongInput.value.trim() && item.jibun_address) {
      const parts = String(item.jibun_address).split(/\s+/);
      const maybeDong = parts.find((t) => /(동|읍|면|리|가)$/.test(t));
      if (maybeDong) dongInput.value = maybeDong;
    }
    options.onAddressSelected({
      address,
      name: item.name,
      dongLabel,
    });
  }

  function hideList() {
    listbox.hidden = true;
    activeIndex = -1;
  }

  function scheduleSearch() {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      void runSearch();
    }, 280);
  }

  function scheduleDongLoad() {
    window.clearTimeout(dongDebounce);
    dongDebounce = window.setTimeout(() => {
      void loadDong(dongInput.value.trim());
    }, 220);
  }

  sidoSel.addEventListener("change", () => {
    void loadSigungu();
  });
  sigunguSel.addEventListener("change", () => {
    dongInput.value = "";
    lastDongLabel = "";
    void loadDong("");
    scheduleSearch();
  });
  dongInput.addEventListener("focus", () => {
    if (sidoSel.value && sigunguSel.value) {
      if (!dongResults.length) void loadDong(dongInput.value.trim());
      else renderDongList(dongResults);
    }
  });
  dongInput.addEventListener("input", () => {
    lastDongLabel = [sidoSel.value, sigunguSel.value, dongInput.value.trim()]
      .filter(Boolean)
      .join(" ");
    scheduleDongLoad();
  });
  dongInput.addEventListener("keydown", (ev) => {
    if (dongList.hidden || !dongResults.length) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      dongActive = Math.min(dongResults.length - 1, dongActive + 1);
      highlightDong();
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      dongActive = Math.max(0, dongActive - 1);
      highlightDong();
    } else if (ev.key === "Enter" && dongActive >= 0) {
      ev.preventDefault();
      selectDong(dongResults[dongActive]);
    } else if (ev.key === "Escape") {
      hideDongList();
    }
  });

  input.addEventListener("input", scheduleSearch);
  input.addEventListener("focus", () => {
    if (currentResults.length) listbox.hidden = false;
  });
  input.addEventListener("keydown", (ev) => {
    if (listbox.hidden || !currentResults.length) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      activeIndex = Math.min(currentResults.length - 1, activeIndex + 1);
      highlightActive();
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      activeIndex = Math.max(0, activeIndex - 1);
      highlightActive();
    } else if (ev.key === "Enter" && activeIndex >= 0) {
      ev.preventDefault();
      selectIndex(activeIndex);
    } else if (ev.key === "Escape") {
      hideList();
    }
  });
  document.addEventListener("click", (ev) => {
    if (!host.contains(ev.target)) {
      hideList();
      hideDongList();
    }
  });

  function highlightActive() {
    listbox.querySelectorAll(".store-picker-option").forEach((n, idx) => {
      n.classList.toggle("is-active", idx === activeIndex);
    });
  }
  function highlightDong() {
    dongList.querySelectorAll(".store-picker-option").forEach((n, idx) => {
      n.classList.toggle("is-active", idx === dongActive);
    });
  }

  void loadSido();

  return {
    root: host,
    input,
    setVisible(on) {
      host.hidden = !on;
      input.required = Boolean(on);
      if (!on) {
        input.value = "";
        selected.hidden = true;
        hideList();
        hideDongList();
        status.textContent = "";
        lastDongLabel = "";
      }
    },
    getAddress() {
      return input.value.trim();
    },
    setAddress(value) {
      input.value = value || "";
    },
    /** Admin label for location_dong when precise location is on. */
    getDongLabel() {
      if (lastDongLabel) return lastDongLabel;
      const parts = [sidoSel.value, sigunguSel.value, dongInput.value.trim()].filter(
        Boolean,
      );
      return parts.join(" ");
    },
  };
}

function makeSelect(id, placeholder) {
  const sel = document.createElement("select");
  sel.id = id;
  sel.className = "store-picker-select";
  fillSelect(sel, [], placeholder);
  return sel;
}

function fillSelect(sel, items, placeholder) {
  sel.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = "";
  opt0.textContent = placeholder;
  sel.appendChild(opt0);
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    sel.appendChild(opt);
  }
}

function wrapField(title, control) {
  const label = document.createElement("label");
  label.className = "store-picker-region-field";
  const span = document.createElement("span");
  span.className = "field-title";
  span.textContent = title;
  label.appendChild(span);
  label.appendChild(control);
  return label;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
