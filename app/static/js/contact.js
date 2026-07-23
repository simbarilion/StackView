(() => {
  const form = document.getElementById("contact-form");
  const statusEl = document.getElementById("form-status");
  const submitBtn = document.getElementById("submit-btn");

  if (!(form instanceof HTMLFormElement) || !(statusEl instanceof HTMLElement) || !(submitBtn instanceof HTMLButtonElement)) {
    return;
  }

  const fields = ["name", "phone", "email", "comment"];

  function setStatus(message, kind) {
    statusEl.textContent = message;
    statusEl.classList.remove("is-ok", "is-error");
    if (kind) {
      statusEl.classList.add(kind);
    }
  }

  function clearInvalid() {
    for (const name of fields) {
      const el = form.elements.namedItem(name);
      if (el instanceof HTMLElement) {
        el.classList.remove("is-invalid");
      }
    }
  }

  function markInvalid(fieldName) {
    const el = form.elements.namedItem(fieldName);
    if (el instanceof HTMLElement) {
      el.classList.add("is-invalid");
    }
  }

  function payloadFromForm() {
    const data = new FormData(form);
    return {
      name: String(data.get("name") || "").trim(),
      phone: String(data.get("phone") || "").trim(),
      email: String(data.get("email") || "").trim(),
      comment: String(data.get("comment") || "").trim(),
    };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearInvalid();
    setStatus("", null);

    const payload = payloadFromForm();
    let hasClientError = false;
    for (const name of fields) {
      const el = form.elements.namedItem(name);
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
        if (!el.checkValidity()) {
          markInvalid(name);
          hasClientError = true;
        }
      }
    }
    if (hasClientError) {
      setStatus("Заполните поля корректно.", "is-error");
      return;
    }

    submitBtn.disabled = true;
    setStatus("Отправляем…", null);

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });

      let body = null;
      try {
        body = await response.json();
      } catch {
        body = null;
      }

      if (response.ok) {
        form.reset();
        const aiNote = body && body.ai_available ? " AI-разбор готов." : "";
        setStatus(`Сообщение принято.${aiNote}`, "is-ok");
        return;
      }

      if (response.status === 422 && body) {
        const details = body.details;
        if (Array.isArray(details)) {
          for (const item of details) {
            if (Array.isArray(item.loc) && item.loc.includes("name")) markInvalid("name");
            if (Array.isArray(item.loc) && item.loc.includes("phone")) markInvalid("phone");
            if (Array.isArray(item.loc) && item.loc.includes("email")) markInvalid("email");
            if (Array.isArray(item.loc) && item.loc.includes("comment")) markInvalid("comment");
          }
        }
        setStatus("Заполните поля корректно.", "is-error");
        return;
      }

      if (response.status === 429) {
        setStatus((body && body.message) || "Слишком много запросов. Попробуйте позже.", "is-error");
        return;
      }

      setStatus((body && body.message) || "Не удалось отправить. Попробуйте ещё раз.", "is-error");
    } catch {
      setStatus("Сеть недоступна. Проверьте соединение.", "is-error");
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
