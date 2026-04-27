function toNumber(value) {
  const parsed = Number.parseFloat(String(value || "0").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatMoney(value) {
  return new Intl.NumberFormat("pt-PT", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function updateLineTotal(row) {
  const quantity = toNumber(row.querySelector("[data-line-quantity]")?.value);
  const unitPrice = toNumber(row.querySelector("[data-line-price]")?.value);
  const discount = toNumber(row.querySelector("[data-line-discount]")?.value);
  const total = Math.max((quantity * unitPrice) - discount, 0);
  const target = row.querySelector("[data-line-total]");

  if (target) {
    target.textContent = `Kz ${formatMoney(total)}`;
  }

  return total;
}

function updateInvoiceSummary(form) {
  const rows = Array.from(form.querySelectorAll("[data-line-item]"));
  const subtotal = rows.reduce((sum, row) => sum + updateLineTotal(row), 0);
  const discount = toNumber(form.querySelector("[name='discount_amount']")?.value);
  const tax = toNumber(form.querySelector("[name='tax_amount']")?.value);
  const total = Math.max(subtotal - discount + tax, 0);

  const subtotalTarget = form.querySelector("[data-summary-subtotal]");
  const totalTarget = form.querySelector("[data-summary-total]");

  if (subtotalTarget) {
    subtotalTarget.textContent = `Subtotal: Kz ${formatMoney(subtotal)}`;
  }

  if (totalTarget) {
    totalTarget.textContent = `Total: Kz ${formatMoney(total)}`;
  }
}

function syncPriceFromProduct(row) {
  const select = row.querySelector("[data-product-select]");
  const priceInput = row.querySelector("[data-line-price]");

  if (!select || !priceInput) {
    return;
  }

  const selectedOption = select.options[select.selectedIndex];
  const suggestedPrice = selectedOption?.dataset?.price;

  if (suggestedPrice && !priceInput.dataset.touched) {
    priceInput.value = Number.parseFloat(suggestedPrice).toFixed(2);
  }
}

function bindRow(row, form) {
  const inputs = row.querySelectorAll("input, select");
  inputs.forEach((input) => {
    input.addEventListener("input", () => {
      if (input.matches("[data-line-price]")) {
        input.dataset.touched = "true";
      }
      updateInvoiceSummary(form);
    });
  });

  const select = row.querySelector("[data-product-select]");
  if (select) {
    select.addEventListener("change", () => {
      syncPriceFromProduct(row);
      updateInvoiceSummary(form);
    });
  }

  const removeButton = row.querySelector("[data-remove-line]");
  if (removeButton) {
    removeButton.addEventListener("click", () => {
      const rows = form.querySelectorAll("[data-line-item]");
      if (rows.length > 1) {
        row.remove();
      } else {
        row.querySelectorAll("input").forEach((input) => {
          input.value = input.name === "quantity" ? "1" : input.name === "item_discount_amount" ? "0.00" : "";
        });
        if (select) {
          select.value = "";
        }
      }
      updateInvoiceSummary(form);
    });
  }

  syncPriceFromProduct(row);
  updateLineTotal(row);
}

function setupInvoiceForm(form) {
  const container = form.querySelector("[data-lines-container]");
  const template = form.querySelector("#invoice-line-template");
  const addButton = form.querySelector("[data-add-line]");

  if (!container || !template || !addButton) {
    return;
  }

  container.querySelectorAll("[data-line-item]").forEach((row) => bindRow(row, form));

  addButton.addEventListener("click", () => {
    const index = container.querySelectorAll("[data-line-item]").length;
    const html = template.innerHTML;
    container.insertAdjacentHTML("beforeend", html);
    const newRow = container.querySelectorAll("[data-line-item]")[index];
    bindRow(newRow, form);
    updateInvoiceSummary(form);
  });

  form.querySelectorAll("[name='discount_amount'], [name='tax_amount']").forEach((input) => {
    input.addEventListener("input", () => updateInvoiceSummary(form));
  });

  updateInvoiceSummary(form);
}

function updateEntryLineTotal(row) {
  const quantity = toNumber(row.querySelector("[name='quantity']")?.value);
  const unitCost = toNumber(row.querySelector("[name='unit_cost']")?.value);
  const total = quantity * unitCost;
  const target = row.querySelector("[data-entry-line-total]");
  if (target) {
    target.textContent = `Kz ${formatMoney(total)}`;
  }
}

function bindEntryRow(row, form) {
  row.querySelectorAll("input, select").forEach((input) => {
    input.addEventListener("input", () => updateEntryLineTotal(row));
  });

  const removeButton = row.querySelector("[data-remove-entry-line]");
  if (removeButton) {
    removeButton.addEventListener("click", () => {
      const rows = form.querySelectorAll("[data-entry-item]");
      if (rows.length > 1) {
        row.remove();
      } else {
        row.querySelectorAll("input").forEach((input) => {
          input.value = input.name === "quantity" ? "1" : "0.00";
        });
        const select = row.querySelector("select");
        if (select) {
          select.value = "";
        }
      }
      updateEntryLineTotal(row);
    });
  }

  updateEntryLineTotal(row);
}

function setupStockEntryForm(form) {
  const container = form.querySelector("[data-entry-lines]");
  const template = form.querySelector("#stock-entry-line-template");
  const addButton = form.querySelector("[data-add-entry-line]");

  if (!container || !template || !addButton) {
    return;
  }

  container.querySelectorAll("[data-entry-item]").forEach((row) => bindEntryRow(row, form));

  addButton.addEventListener("click", () => {
    container.insertAdjacentHTML("beforeend", template.innerHTML);
    const rows = container.querySelectorAll("[data-entry-item]");
    bindEntryRow(rows[rows.length - 1], form);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-invoice-form]").forEach((form) => setupInvoiceForm(form));
  document.querySelectorAll("[data-stock-entry-form]").forEach((form) => setupStockEntryForm(form));
});
