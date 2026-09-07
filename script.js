(() => {
  "use strict";
  const rawUrl = window.DRUK_CONFIG?.betaFormUrl?.trim();
  let formUrl = "";
  if (rawUrl) {
    try {
      const url = new URL(rawUrl);
      if (url.protocol === "https:") formUrl = url.href;
    } catch { /* An unset or invalid URL uses the honest beta placeholder. */ }
  }
  const status = document.getElementById("beta-status");
  document.querySelectorAll("[data-beta]").forEach((link) => {
    if (formUrl) {
      link.href = formUrl;
      return;
    }
    link.addEventListener("click", (event) => {
      event.preventDefault();
      status.textContent = "Запись в бету скоро откроется. Загляни чуть позже 🌿";
      status.tabIndex = -1;
      status.focus({ preventScroll: true });
      document.getElementById("join").scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
        block: "center"
      });
    });
  });
})();
