export function createSettingsSystem({
  settingsDialog,
  previewSystem,
  previewViewers,
  cwdValueInput,
  modelSourceValueInput,
  previewDirInput,
  previewDirSetBtn,
  previewDirResetBtn,
  previewDirWarningEl,
  autoReloadIntervalInput,
  getAutoReloadIntervalMs,
  setAutoReloadIntervalMs,
  initModels,
}) {
  let activeTab = "general";

  function activateTab(tabName) {
    if (!settingsDialog) return;
    activeTab = tabName;
    const tabButtons = settingsDialog.querySelectorAll(".tab-btn");
    const tabPanels = settingsDialog.querySelectorAll(".tab-panel");
    tabButtons.forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.tab === tabName);
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.tabPanel === tabName);
    });
    if (previewSystem) {
      const viewer = previewViewers?.[tabName];
      if (viewer) {
        previewSystem.bindViewer(viewer);
        previewSystem.updateSize();
        previewSystem.syncFromMain();
      }
    }
  }

  function initTabs(defaultTab = "general") {
    if (!settingsDialog) return;
    const tabButtons = settingsDialog.querySelectorAll(".tab-btn");
    tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        activateTab(btn.dataset.tab);
      });
    });
    activateTab(defaultTab);
  }

  function refreshPreviewInfo() {
    fetch("/preview_info.json")
      .then((resp) => resp.json())
      .then((data) => {
        if (cwdValueInput) cwdValueInput.value = data?.cwd || "";
        const relativePath =
          data?.preview_dir && data?.cwd
            ? data.preview_dir.replace(data.cwd || "", "").replace(/^\//, "")
            : "";
        if (modelSourceValueInput) {
          if (data?.source === "demo") {
            modelSourceValueInput.value = "Demo Device";
          } else if (data?.source === "cwd/_visualization") {
            modelSourceValueInput.value = `Default (${relativePath})`;
          } else if (data?.source === "custom") {
            modelSourceValueInput.value = relativePath;
          } else {
            modelSourceValueInput.value = "";
          }
        }
        if (previewDirInput) {
          previewDirInput.value = relativePath || "";
        }
      })
      .catch(() => {
        if (cwdValueInput) cwdValueInput.value = "";
        if (modelSourceValueInput) modelSourceValueInput.value = "";
      });
  }

  function initGeneralSettings() {
    refreshPreviewInfo();

    const setWarning = (message = "") => {
      if (!previewDirWarningEl) return;
      previewDirWarningEl.textContent = message;
    };

    if (previewDirSetBtn && previewDirInput) {
      previewDirSetBtn.addEventListener("click", async () => {
        setWarning("");
        const pathValue = previewDirInput.value.trim();
        const resp = await fetch("/set_preview_dir", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: pathValue }),
        });
        if (resp.ok) {
          await initModels();
          refreshPreviewInfo();
        } else {
          const data = await resp.json().catch(() => null);
          setWarning(data?.error || "Unable to set preview folder");
        }
      });
    }

    if (previewDirResetBtn) {
      previewDirResetBtn.addEventListener("click", async () => {
        setWarning("");
        const resp = await fetch("/set_preview_dir", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: "" }),
        });
        if (resp.ok) {
          await initModels();
          refreshPreviewInfo();
        } else {
          setWarning("Unable to reset preview folder");
        }
      });
    }

    if (autoReloadIntervalInput) {
      autoReloadIntervalInput.value = String(getAutoReloadIntervalMs());
      autoReloadIntervalInput.addEventListener("change", () => {
        const next = Number.parseInt(autoReloadIntervalInput.value, 10);
        if (!Number.isFinite(next) || next < 250) return;
        setAutoReloadIntervalMs(next);
      });
    }
  }

  return {
    initTabs,
    activateTab,
    getActiveTab: () => activeTab,
    initGeneralSettings,
    refreshPreviewInfo,
  };
}
