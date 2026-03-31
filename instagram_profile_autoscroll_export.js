(() => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const username = (location.pathname.split("/").filter(Boolean)[0] || "perfil").replace(/[^\w.-]+/g, "_");
  const startedAt = new Date();
  const state = {
    urls: new Set(),
    stableRounds: 0,
    lastHeight: 0,
    lastCount: 0,
  };

  const overlay = document.createElement("div");
  overlay.id = "__ig_scroller_overlay__";
  overlay.style.cssText = [
    "position:fixed",
    "right:16px",
    "bottom:16px",
    "z-index:2147483647",
    "width:320px",
    "padding:14px 16px",
    "border-radius:14px",
    "background:rgba(17, 24, 39, 0.96)",
    "color:#f9fafb",
    "font:13px/1.45 -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif",
    "box-shadow:0 12px 36px rgba(0,0,0,0.32)",
    "white-space:pre-wrap",
  ].join(";");
  document.body.appendChild(overlay);

  const setOverlay = (message) => {
    overlay.textContent = message;
  };

  const collectPostUrls = () => {
    const anchors = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"], a[href*="/tv/"]');
    anchors.forEach((anchor) => {
      const href = anchor.getAttribute("href") || "";
      if (!href) return;
      try {
        const absolute = new URL(href, location.origin);
        absolute.search = "";
        absolute.hash = "";
        const clean = absolute.toString().replace(/\/?$/, "/");
        state.urls.add(clean);
      } catch (error) {
        console.warn("Falha ao normalizar link:", href, error);
      }
    });
  };

  const currentHeight = () => Math.max(
    document.body.scrollHeight,
    document.documentElement.scrollHeight,
    document.body.offsetHeight,
    document.documentElement.offsetHeight
  );

  const exportUrls = async () => {
    const sorted = Array.from(state.urls).sort();
    const payload = sorted.join("\n");
    const fileName = `instagram_posts_${username}_${new Date().toISOString().replace(/[:.]/g, "-")}.txt`;

    try {
      await navigator.clipboard.writeText(payload);
    } catch (error) {
      console.warn("Nao foi possivel copiar para a area de transferencia.", error);
    }

    const blob = new Blob([payload], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);

    const seconds = Math.round((Date.now() - startedAt.getTime()) / 1000);
    setOverlay(
      [
        "Coleta concluida.",
        `Posts encontrados: ${sorted.length}`,
        `Tempo total: ${seconds}s`,
        "",
        "O .txt foi baixado e os links foram copiados para a area de transferencia.",
        "Volte ao app para rodar o downloader.",
      ].join("\n")
    );
  };

  const run = async () => {
    setOverlay(
      [
        "Auto scroller em execucao...",
        "Nao troque de aba ate terminar.",
        "",
        "Dica: deixe o perfil aberto na grade de posts.",
      ].join("\n")
    );

    collectPostUrls();
    state.lastHeight = currentHeight();
    state.lastCount = state.urls.size;

    while (state.stableRounds < 8) {
      window.scrollTo({ top: currentHeight(), behavior: "auto" });
      await sleep(1500);
      collectPostUrls();

      const height = currentHeight();
      const count = state.urls.size;
      if (height === state.lastHeight && count === state.lastCount) {
        state.stableRounds += 1;
      } else {
        state.stableRounds = 0;
      }

      state.lastHeight = height;
      state.lastCount = count;

      setOverlay(
        [
          "Auto scroller em execucao...",
          `Posts encontrados: ${count}`,
          `Rodadas estaveis: ${state.stableRounds}/8`,
          "",
          "O script vai parar sozinho quando chegar ao fim.",
        ].join("\n")
      );
    }

    await exportUrls();
  };

  run().catch((error) => {
    console.error(error);
    setOverlay(`Falha no auto scroller:\n${error && error.message ? error.message : String(error)}`);
  });
})();
