/**
 * Vista "Informes": carga la vista previa del informe de activos en un
 * iframe y lo envía por email a través de la API.
 */
(function () {
  "use strict";

  const page = document.getElementById("informes-page");
  if (!page) return; // esta página no está montada

  const previewBtn = document.getElementById("preview-btn");
  const sendForm = document.getElementById("send-form");
  const sendBtn = document.getElementById("send-btn");
  const emailInput = document.getElementById("email-input");
  const statusEl = document.getElementById("informes-status");
  const previewEl = document.getElementById("informes-preview");

  function setStatus(message, isError) {
    statusEl.hidden = !message;
    statusEl.textContent = message || "";
    statusEl.classList.toggle("is-error", Boolean(isError));
  }

  function selectedWatchlists() {
    return Array.from(page.querySelectorAll('input[name="watchlists"]:checked')).map((el) => el.value);
  }

  function requireWatchlists() {
    const slugs = selectedWatchlists();
    if (!slugs.length) setStatus("Selecciona al menos una watchlist.", true);
    return slugs;
  }

  previewBtn.addEventListener("click", () => {
    const slugs = requireWatchlists();
    if (!slugs.length) return;

    setStatus("Generando informe…");
    previewBtn.disabled = true;
    previewEl.onload = () => {
      previewBtn.disabled = false;
      setStatus("");
    };
    previewEl.hidden = false;
    previewEl.src = `/api/report/preview?watchlists=${encodeURIComponent(slugs.join(","))}`;
  });

  sendForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const slugs = requireWatchlists();
    if (!slugs.length) return;

    const to = emailInput.value.trim();
    setStatus(`Enviando informe a ${to}…`);
    sendBtn.disabled = true;
    try {
      const response = await fetch("/api/email/send-assets-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to, watchlists: slugs }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `Error ${response.status}`);
      setStatus(`Informe enviado a ${to}.`);
    } catch (err) {
      setStatus(`No se pudo enviar el informe: ${err.message}`, true);
    } finally {
      sendBtn.disabled = false;
    }
  });
})();
