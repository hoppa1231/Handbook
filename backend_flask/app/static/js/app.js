const API_BASE = "/api";

const state = {
  suppliers: [],
  supplierFilter: "",
  products: [],
  productFilter: "",
  prices: [],
  priceFilter: "",
  selectedSupplierId: null,
  selectedProductId: null,
  selectedPriceId: null,
  activeTab: "suppliers",
};

const notificationEl = document.querySelector("#notification");

function showMessage(message, type = "success") {
  if (!notificationEl) return;
  notificationEl.textContent = message;
  notificationEl.className = type;
  setTimeout(() => {
    notificationEl.textContent = "";
    notificationEl.className = "";
  }, 4000);
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data?.message ? `: ${data.message}` : "";
    } catch {
      // ignore parsing errors
    }
    throw new Error(`Ошибка запроса (${response.status})${detail}`);
  }

  return response.json();
}

function supplierMap() {
  return new Map(state.suppliers.map((supplier) => [supplier.id, supplier]));
}

function productMap() {
  return new Map(state.products.map((product) => [product.id, product]));
}

function createActionButton(label, className, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.className = className ? `small ${className}` : "small";
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    handler();
  });
  return button;
}

function switchTab(tabId, { silent = false } = {}) {
  state.activeTab = tabId;
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.tab === tabId);
  });
  if (tabId === "competition") {
    const select = document.querySelector("#competition-product-select");
    if (select) {
      const hasOption = Array.from(select.options).some(
        (option) => Number(option.value) === state.selectedProductId
      );
      if (!select.value && state.selectedProductId && hasOption) {
        select.value = String(state.selectedProductId);
      }
      if (select.value) {
        refreshCompetition({ silent: true }).catch((error) => {
          if (!silent) showMessage(error.message, "error");
        });
      } else {
        renderCompetition([], "Выберите товар, чтобы увидеть предложения");
      }
    }
  }
}

async function loadSuppliers() {
  state.suppliers = await fetchJSON(`${API_BASE}/suppliers`);
  renderSuppliers();
  populateSupplierSelects();
}

function renderSuppliers() {
  const tbody = document.querySelector("#suppliers-table tbody");
  const filter = state.supplierFilter.trim().toLowerCase();
  const suppliers = filter
    ? state.suppliers.filter((supplier) => {
        const values = [
          supplier.name,
          supplier.address,
          supplier.contact,
          supplier.website,
        ].filter(Boolean);
        return values.some((value) => value.toLowerCase().includes(filter));
      })
    : [...state.suppliers];

  tbody.innerHTML = "";

  if (!suppliers.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="table-empty" colspan="5">По вашему запросу ничего не найдено</td>';
    tbody.appendChild(tr);
    return;
  }

  suppliers.forEach((supplier) => {
    const tr = document.createElement("tr");
    tr.dataset.id = supplier.id;
    tr.innerHTML = `
      <td>${supplier.id}</td>
      <td>${supplier.name ?? ""}</td>
      <td>${supplier.contact ?? ""}</td>
      <td>${supplier.rating ?? ""}</td>
    `;
    tr.addEventListener("click", () => selectSupplier(supplier.id));
    if (state.selectedSupplierId === supplier.id) {
      tr.classList.add("selected");
    }

    const actionsTd = document.createElement("td");
    actionsTd.className = "actions-col";
    const deleteBtn = createActionButton("Удалить", "danger", () => deleteSupplier(supplier.id));
    actionsTd.appendChild(deleteBtn);
    tr.appendChild(actionsTd);

    tbody.appendChild(tr);
  });
}

function populateSupplierSelects() {
  const select = document.querySelector("#price-supplier");
  if (!select) return;
  const options =
    '<option value="">Выберите поставщика</option>' +
    state.suppliers
      .map((supplier) => `<option value="${supplier.id}">${supplier.name}</option>`)
      .join("");
  select.innerHTML = options;
}

function selectSupplier(id) {
  state.selectedSupplierId = id;
  const supplier = supplierMap().get(id);
  if (!supplier) return;
  document.querySelector("#supplier-id").value = supplier.id;
  document.querySelector("#supplier-name").value = supplier.name ?? "";
  document.querySelector("#supplier-address").value = supplier.address ?? "";
  document.querySelector("#supplier-contact").value = supplier.contact ?? "";
  document.querySelector("#supplier-website").value = supplier.website ?? "";
  document.querySelector("#supplier-rating").value =
    supplier.rating !== null && supplier.rating !== undefined ? supplier.rating : "";
  renderSuppliers();
}

function resetSupplierForm() {
  state.selectedSupplierId = null;
  const form = document.querySelector("#supplier-form");
  form?.reset();
  const idField = document.querySelector("#supplier-id");
  if (idField) idField.value = "";
  renderSuppliers();
}

async function submitSupplier(event) {
  event.preventDefault();
  const name = document.querySelector("#supplier-name")?.value.trim();
  if (!name) {
    showMessage("Введите название поставщика", "error");
    return;
  }
  const payload = {
    name,
    address: document.querySelector("#supplier-address")?.value.trim() || null,
    contact: document.querySelector("#supplier-contact")?.value.trim() || null,
    website: document.querySelector("#supplier-website")?.value.trim() || null,
    rating: document.querySelector("#supplier-rating")?.value
      ? Number(document.querySelector("#supplier-rating").value)
      : null,
  };

  try {
    if (state.selectedSupplierId) {
      await fetchJSON(`${API_BASE}/suppliers/${state.selectedSupplierId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showMessage("Поставщик обновлён");
    } else {
      await fetchJSON(`${API_BASE}/suppliers`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showMessage("Поставщик создан");
    }
    await loadSuppliers();
    await loadPrices();
    resetSupplierForm();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function deleteSupplier(id) {
  const targetId = id ?? state.selectedSupplierId;
  if (!targetId) {
    showMessage("Выберите поставщика для удаления", "error");
    return;
  }
  if (!confirm("Удалить выбранного поставщика?")) return;

  try {
    await fetchJSON(`${API_BASE}/suppliers/${targetId}`, { method: "DELETE" });
    showMessage("Поставщик удалён");
    if (state.selectedSupplierId === targetId) {
      resetSupplierForm();
    }
    await loadSuppliers();
    await loadPrices();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadProducts() {
  state.products = await fetchJSON(`${API_BASE}/products`);
  if (state.selectedProductId && !state.products.some((product) => product.id === state.selectedProductId)) {
    state.selectedProductId = null;
  }
  renderProducts();
  populateProductSelects();
}

function renderProducts() {
  const tbody = document.querySelector("#products-table tbody");
  const filter = state.productFilter.trim().toLowerCase();
  const products = filter
    ? state.products.filter((product) => {
        const values = [
          product.partNumber,
          product.name,
          product.brand,
          product.model,
          product.comment,
        ].filter(Boolean);
        return values.some((value) => value.toLowerCase().includes(filter));
      })
    : [...state.products];

  tbody.innerHTML = "";

  if (!products.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="table-empty" colspan="5">По вашему запросу ничего не найдено</td>';
    tbody.appendChild(tr);
    return;
  }

  products.forEach((product) => {
    const tr = document.createElement("tr");
    tr.dataset.id = product.id;
    tr.innerHTML = `
      <td>${product.id}</td>
      <td>${product.partNumber ?? ""}</td>
      <td>${product.name ?? ""}</td>
      <td>${product.brand ?? ""}</td>
    `;
    tr.addEventListener("click", () => selectProduct(product.id));
    if (state.selectedProductId === product.id) {
      tr.classList.add("selected");
    }

    const actionsTd = document.createElement("td");
    actionsTd.className = "actions-col";
    const deleteBtn = createActionButton("Удалить", "danger", () => deleteProduct(product.id));
    actionsTd.appendChild(deleteBtn);
    tr.appendChild(actionsTd);

    tbody.appendChild(tr);
  });
}

function populateProductSelects() {
  const competitionSelect = document.querySelector("#competition-product-select");
  const priceSelect = document.querySelector("#price-product");
  const options =
    '<option value="">Выберите товар</option>' +
    state.products
      .map((product) => `<option value="${product.id}">${product.partNumber} — ${product.name}</option>`)
      .join("");
  if (competitionSelect) {
    competitionSelect.innerHTML = options;
    if (state.selectedProductId && state.products.some((product) => product.id === state.selectedProductId)) {
      competitionSelect.value = String(state.selectedProductId);
    }
  }
  if (priceSelect) {
    priceSelect.innerHTML = options;
  }
}

function selectProduct(id) {
  state.selectedProductId = id;
  const product = productMap().get(id);
  if (!product) return;
  document.querySelector("#product-id").value = product.id;
  document.querySelector("#product-part-number").value = product.partNumber ?? "";
  document.querySelector("#product-name").value = product.name ?? "";
  document.querySelector("#product-brand").value = product.brand ?? "";
  document.querySelector("#product-model").value = product.model ?? "";
  document.querySelector("#product-serial").value =
    product.serialNumber !== null && product.serialNumber !== undefined
      ? product.serialNumber
      : "";
  document.querySelector("#product-scheme").value = product.scheme ?? "";
  document.querySelector("#product-pos-scheme").value = product.posScheme ?? "";
  document.querySelector("#product-material").value = product.material ?? "";
  document.querySelector("#product-size").value = product.size ?? "";
  document.querySelector("#product-comment").value = product.comment ?? "";
  document.querySelector("#product-category").value = product.category ?? "";
  renderProducts();
}

function resetProductForm() {
  state.selectedProductId = null;
  const form = document.querySelector("#product-form");
  form?.reset();
  const idField = document.querySelector("#product-id");
  if (idField) idField.value = "";
  renderProducts();
}

async function submitProduct(event) {
  event.preventDefault();
  const partNumber = document.querySelector("#product-part-number")?.value.trim();
  const name = document.querySelector("#product-name")?.value.trim();
  if (!partNumber) {
    showMessage("Введите артикул", "error");
    return;
  }
  if (!name) {
    showMessage("Введите название товара", "error");
    return;
  }

  const payload = {
    partNumber,
    name,
    brand: document.querySelector("#product-brand")?.value.trim() || null,
    model: document.querySelector("#product-model")?.value.trim() || null,
    serialNumber: document.querySelector("#product-serial")?.value.trim(),
    scheme: document.querySelector("#product-scheme")?.value.trim() || null,
    posScheme: document.querySelector("#product-pos-scheme")?.value.trim() || null,
    material: document.querySelector("#product-material")?.value.trim() || null,
    size: document.querySelector("#product-size")?.value.trim() || null,
    comment: document.querySelector("#product-comment")?.value.trim() || null,
    category: document.querySelector("#product-category")?.value.trim() || null,
  };
  if (payload.serialNumber === "") {
    delete payload.serialNumber;
  }

  try {
    if (state.selectedProductId) {
      await fetchJSON(`${API_BASE}/products/${state.selectedProductId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showMessage("Товар обновлён");
    } else {
      await fetchJSON(`${API_BASE}/products`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showMessage("Товар создан");
    }
    await loadProducts();
    await loadPrices();
    resetProductForm();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function deleteProduct(id) {
  const targetId = id ?? state.selectedProductId;
  if (!targetId) {
    showMessage("Выберите товар для удаления", "error");
    return;
  }
  if (!confirm("Удалить выбранный товар?")) return;
  try {
    await fetchJSON(`${API_BASE}/products/${targetId}`, { method: "DELETE" });
    showMessage("Товар удалён");
    if (state.selectedProductId === targetId) {
      resetProductForm();
    }
    await loadProducts();
    await loadPrices();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function refreshCompetition({ silent = false } = {}) {
  const select = document.querySelector("#competition-product-select");
  if (!select) return;
  const candidateId = Number(select.value || state.selectedProductId);
  if (!candidateId) {
    renderCompetition([], "Выберите товар, чтобы увидеть предложения");
    if (!silent) {
      showMessage("Выберите товар для просмотра конкурентной карты", "error");
    }
    return;
  }

  if (!select.value) {
    const hasOption = Array.from(select.options).some((option) => Number(option.value) === candidateId);
    if (hasOption) {
      select.value = String(candidateId);
    }
  }

  state.selectedProductId = candidateId;

  try {
    const data = await fetchJSON(`${API_BASE}/products/${candidateId}/competition`);
    renderCompetition(data.offers || []);
  } catch (error) {
    renderCompetition([], "Не удалось загрузить данные");
    if (!silent) {
      showMessage(error.message, "error");
    }
  }
}

function renderCompetition(offers, emptyMessage = "Предложений пока нет") {
  const tbody = document.querySelector("#competition-table tbody");
  tbody.innerHTML = "";
  if (!offers.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="table-empty" colspan="4">${emptyMessage}</td>`;
    tbody.appendChild(tr);
    return;
  }

  offers.forEach((offer) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${offer.supplierName ?? offer.supplierId}</td>
      <td>${offer.totalPrice ?? ""}</td>
      <td>${offer.leadTimeDays ?? ""}</td>
      <td>${offer.currency ?? ""}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadPrices() {
  state.prices = await fetchJSON(`${API_BASE}/supplier-prices`);
  renderPrices();
}

function renderPrices() {
  const tbody = document.querySelector("#prices-table tbody");
  const filter = state.priceFilter.trim().toLowerCase();
  const productsLookup = productMap();
  const suppliersLookup = supplierMap();
  const prices = filter
    ? state.prices.filter((price) => {
        const product = productsLookup.get(price.productId);
        const supplier = suppliersLookup.get(price.supplierId);
        const values = [
          price.totalPrice?.toString(),
          price.currency,
          product?.partNumber,
          product?.name,
          supplier?.name,
        ].filter(Boolean);
        return values.some((value) => value.toLowerCase().includes(filter));
      })
    : [...state.prices];

  tbody.innerHTML = "";

  if (!prices.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="table-empty" colspan="7">По вашему запросу ничего не найдено</td>';
    tbody.appendChild(tr);
    return;
  }

  prices.forEach((price) => {
    const tr = document.createElement("tr");
    tr.dataset.id = price.id;
    const product = productsLookup.get(price.productId);
    const supplier = suppliersLookup.get(price.supplierId);
    tr.innerHTML = `
      <td>${price.id}</td>
      <td>${product ? `${product.partNumber} — ${product.name}` : price.productId}</td>
      <td>${supplier ? supplier.name : price.supplierId}</td>
      <td>${price.totalPrice ?? ""}</td>
      <td>${price.leadTimeDays ?? ""}</td>
      <td>${price.currency ?? ""}</td>
    `;
    tr.addEventListener("click", () => selectPrice(price.id));
    if (state.selectedPriceId === price.id) {
      tr.classList.add("selected");
    }

    const actionsTd = document.createElement("td");
    actionsTd.className = "actions-col";
    const deleteBtn = createActionButton("Удалить", "danger", () => deletePrice(price.id));
    actionsTd.appendChild(deleteBtn);
    tr.appendChild(actionsTd);

    tbody.appendChild(tr);
  });
}

function selectPrice(id) {
  state.selectedPriceId = id;
  const price = state.prices.find((item) => item.id === id);
  if (!price) return;
  document.querySelector("#price-id").value = price.id;
  document.querySelector("#price-product").value = price.productId;
  document.querySelector("#price-supplier").value = price.supplierId;
  document.querySelector("#price-total").value =
    price.totalPrice !== null && price.totalPrice !== undefined ? price.totalPrice : "";
  document.querySelector("#price-lead").value =
    price.leadTimeDays !== null && price.leadTimeDays !== undefined ? price.leadTimeDays : "";
  document.querySelector("#price-currency").value = price.currency ?? "";
  renderPrices();
}

function resetPriceForm() {
  state.selectedPriceId = null;
  const form = document.querySelector("#price-form");
  form?.reset();
  const idField = document.querySelector("#price-id");
  if (idField) idField.value = "";
  renderPrices();
}

async function submitPrice(event) {
  event.preventDefault();
  const productId = Number(document.querySelector("#price-product")?.value);
  const supplierId = Number(document.querySelector("#price-supplier")?.value);
  const totalPriceValue = document.querySelector("#price-total")?.value ?? "";
  const leadDaysValue = document.querySelector("#price-lead")?.value ?? "";
  const currency = document.querySelector("#price-currency")?.value.trim() || null;

  if (!productId || !supplierId) {
    showMessage("Выберите товар и поставщика", "error");
    return;
  }

  const payload = {
    productId,
    supplierId,
    totalPrice: totalPriceValue === "" ? null : Number(totalPriceValue),
    leadTimeDays: leadDaysValue === "" ? null : Number(leadDaysValue),
    currency,
  };

  try {
    if (state.selectedPriceId) {
      await fetchJSON(`${API_BASE}/supplier-prices/${state.selectedPriceId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showMessage("Запись обновлена");
    } else {
      await fetchJSON(`${API_BASE}/supplier-prices`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showMessage("Запись добавлена");
    }
    await loadPrices();
    await refreshCompetition({ silent: true });
    resetPriceForm();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function deletePrice(id) {
  const targetId = id ?? state.selectedPriceId;
  if (!targetId) {
    showMessage("Выберите запись для удаления", "error");
    return;
  }
  if (!confirm("Удалить выбранную запись о цене?")) return;
  try {
    await fetchJSON(`${API_BASE}/supplier-prices/${targetId}`, { method: "DELETE" });
    showMessage("Запись удалена");
    if (state.selectedPriceId === targetId) {
      resetPriceForm();
    }
    await loadPrices();
    await refreshCompetition({ silent: true });
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function bindEvents() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  document.querySelector("#supplier-form")?.addEventListener("submit", submitSupplier);
  document.querySelector("#supplier-reset")?.addEventListener("click", resetSupplierForm);
  document.querySelector("#supplier-search")?.addEventListener("input", (event) => {
    state.supplierFilter = event.target.value;
    renderSuppliers();
  });

  document.querySelector("#product-form")?.addEventListener("submit", submitProduct);
  document.querySelector("#product-reset")?.addEventListener("click", resetProductForm);
  document.querySelector("#product-search")?.addEventListener("input", (event) => {
    state.productFilter = event.target.value;
    renderProducts();
  });

  document.querySelector("#competition-refresh")?.addEventListener("click", () => refreshCompetition());
  document.querySelector("#competition-product-select")?.addEventListener("change", () => refreshCompetition());

  document.querySelector("#price-form")?.addEventListener("submit", submitPrice);
  document.querySelector("#price-reset")?.addEventListener("click", resetPriceForm);
  document.querySelector("#price-search")?.addEventListener("input", (event) => {
    state.priceFilter = event.target.value;
    renderPrices();
  });
}

async function bootstrap() {
  bindEvents();
  try {
    await Promise.all([loadSuppliers(), loadProducts()]);
    await loadPrices();
  } catch (error) {
    showMessage(error.message, "error");
  }
  switchTab(state.activeTab, {silent: true});
}

bootstrap();
