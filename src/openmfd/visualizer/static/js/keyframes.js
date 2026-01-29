const KEYFRAME_STORAGE_KEY = 'openmfd_keyframes_v1';

export function createKeyframeSystem({
  cameraSystem,
  lightSystem = null,
  settingsSystem = null,
  settingsDialog = null,
  settingsDialogClose = null,
}) {
  let keyframes = [];
  let activeKeyframeIndex = null;
  let isPanelOpen = false;
  let isEditing = false;
  let editingIndex = null;
  let prevCameraState = null;
  let prevLightState = null;

  let panelEl = null;
  let toggleBtn = null;
  let listEl = null;
  let emptyEl = null;
  let addBtn = null;
  let removeBtn = null;

  let settingsDialogEl = settingsDialog;
  let settingsDialogCloseBtn = settingsDialogClose;
  let settingsSystemRef = settingsSystem;
  let lightSystemRef = lightSystem;
  let settingsTitleEl = null;
  let cameraListEl = null;
  let addCameraBtnSettingsEl = null;
  let removeCameraBtnSettingsEl = null;

  let prevTitleText = null;
  let prevTitleDisplay = null;
  let prevCameraListDisplay = null;
  let prevAddCameraDisplay = null;
  let prevRemoveCameraDisplay = null;
  let hiddenTabButtons = [];
  let hiddenTabPanels = [];
  let globalLightStateBeforeKeyframe = null;

  function restoreDialogChrome() {
    if (settingsTitleEl) {
      settingsTitleEl.textContent = prevTitleText || 'Settings';
      settingsTitleEl.style.display = prevTitleDisplay || '';
    }
    hiddenTabButtons.forEach(({ el, display }) => {
      el.style.display = display || '';
    });
    hiddenTabPanels.forEach(({ el, display }) => {
      el.style.display = display || '';
    });
    hiddenTabButtons = [];
    hiddenTabPanels = [];

    if (cameraListEl) {
      cameraListEl.style.display = prevCameraListDisplay || '';
    }
    if (addCameraBtnSettingsEl) {
      addCameraBtnSettingsEl.style.display = prevAddCameraDisplay || '';
    }
    if (removeCameraBtnSettingsEl) {
      removeCameraBtnSettingsEl.style.display = prevRemoveCameraDisplay || '';
    }
  }

  function exitKeyframeEditing({
    restoreCamera = true,
    restoreLights = true,
    clearSelection = false,
    activateGlobalTab = false,
  } = {}) {
    if (!isEditing) return;

    if (restoreCamera || restoreLights) {
      const frame = normalizeKeyframe(keyframes[editingIndex]);
      frame.camera = cameraSystem.getCameraState();
      frame.lights = lightSystemRef ? lightSystemRef.getLightState() : frame.lights;
      keyframes[editingIndex] = frame;
      saveKeyframes();
      renderList();

      if (restoreCamera && prevCameraState) {
        cameraSystem.applyExternalCameraState(prevCameraState);
      }
      if (restoreLights && prevLightState && lightSystemRef) {
        lightSystemRef.applyLightState(prevLightState);
      }
    }

    isEditing = false;
    editingIndex = null;
    prevCameraState = null;
    prevLightState = null;

    restoreDialogChrome();

    if (clearSelection) {
      clearSelection();
    } else {
      cameraSystem.refreshUpdateButton();
    }

    if (activateGlobalTab && settingsSystemRef) {
      settingsSystemRef.activateTab('general');
    }

    cameraSystem.updateActiveCameraStateFromControls();
    cameraSystem.updateCameraHelper();
    if (lightSystemRef) {
      lightSystemRef.updateDirectionalLightTargets();
    }
  }

  function normalizeKeyframe(raw) {
    if (!raw) {
      return { camera: cameraSystem.getCameraState(), lights: null };
    }
    if (raw.camera || raw.lights) {
      return {
        camera: raw.camera || raw,
        lights: raw.lights || null,
      };
    }
    if (raw.pos && raw.target) {
      return { camera: raw, lights: null };
    }
    return { camera: cameraSystem.getCameraState(), lights: null };
  }

  function saveKeyframes() {
    localStorage.setItem(
      KEYFRAME_STORAGE_KEY,
      JSON.stringify({ keyframes, activeIndex: activeKeyframeIndex })
    );
  }

  function loadKeyframes() {
    const saved = localStorage.getItem(KEYFRAME_STORAGE_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed.keyframes)) {
        keyframes = parsed.keyframes.map((frame) => normalizeKeyframe(frame));
      }
      activeKeyframeIndex = null;
    } catch (e) {
      // ignore
    }
  }

  function updateEmptyState() {
    if (!emptyEl) return;
    emptyEl.style.display = keyframes.length ? 'none' : '';
  }

  function renderList() {
    if (!listEl) return;
    listEl.innerHTML = '';
    keyframes.forEach((state, index) => {
      const row = document.createElement('div');
      row.className = 'keyframe-row';

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'control-btn icon-btn keyframe-edit-btn';
      editBtn.title = `Edit Keyframe ${index + 1}`;
      editBtn.innerHTML = '<i class="fa-solid fa-pen"></i>';
      editBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        openEditor(index);
      });

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'camera-btn keyframe-btn keyframe-select-btn';
      btn.innerHTML = `Keyframe ${index + 1} <span>Camera</span>`;
      if (index === activeKeyframeIndex) {
        btn.classList.add('is-active');
      }
      btn.addEventListener('click', () => {
        selectKeyframe(index);
      });

      row.appendChild(editBtn);
      row.appendChild(btn);
      listEl.appendChild(row);
    });
    updateEmptyState();
    if (removeBtn) {
      removeBtn.disabled = activeKeyframeIndex === null || keyframes.length === 0;
    }
  }

  function setPanelOpen(open) {
    isPanelOpen = !!open;
    if (panelEl) {
      panelEl.style.display = isPanelOpen ? '' : 'none';
    }
    if (toggleBtn) {
      toggleBtn.classList.toggle('is-active', isPanelOpen);
    }
  }

  function selectKeyframe(index) {
    if (!Number.isInteger(index) || index < 0 || index >= keyframes.length) return;
    if (activeKeyframeIndex === null && lightSystemRef) {
      globalLightStateBeforeKeyframe = lightSystemRef.getLightState();
    }
    activeKeyframeIndex = index;
    const frame = normalizeKeyframe(keyframes[index]);
    keyframes[index] = frame;
    cameraSystem.setDirtyStateProvider(() => keyframes[activeKeyframeIndex]?.camera || null);
    if (frame.camera) {
      cameraSystem.applyExternalCameraState(frame.camera);
    }
    if (frame.lights && lightSystemRef) {
      lightSystemRef.applyLightState(frame.lights);
    }
    renderList();
    cameraSystem.refreshUpdateButton();
    saveKeyframes();
  }

  function clearSelection() {
    activeKeyframeIndex = null;
    cameraSystem.setDirtyStateProvider(null);
    renderList();
    cameraSystem.refreshUpdateButton();
    if (globalLightStateBeforeKeyframe && lightSystemRef) {
      lightSystemRef.applyLightState(globalLightStateBeforeKeyframe);
    }
    globalLightStateBeforeKeyframe = null;
    saveKeyframes();
  }

  function addKeyframe() {
    const state = cameraSystem.getCameraState();
    const lights = lightSystemRef ? lightSystemRef.getLightState() : null;
    keyframes.push({ camera: state, lights });
    selectKeyframe(keyframes.length - 1);
    saveKeyframes();
  }

  function removeActiveKeyframe() {
    if (activeKeyframeIndex === null) return;
    if (activeKeyframeIndex < 0 || activeKeyframeIndex >= keyframes.length) return;
    keyframes.splice(activeKeyframeIndex, 1);
    if (!keyframes.length) {
      clearSelection();
      return;
    }
    const nextIndex = Math.min(activeKeyframeIndex, keyframes.length - 1);
    selectKeyframe(nextIndex);
    saveKeyframes();
  }

  cameraSystem.setUpdateButtonLabelProvider(() => {
    if (activeKeyframeIndex === null) return null;
    return `Update Keyframe ${activeKeyframeIndex + 1}`;
  });

  cameraSystem.setUpdateButtonHandler(() => {
    if (activeKeyframeIndex === null) return false;
    const frame = normalizeKeyframe(keyframes[activeKeyframeIndex]);
    frame.camera = cameraSystem.getCameraState();
    keyframes[activeKeyframeIndex] = frame;
    renderList();
    saveKeyframes();
    cameraSystem.updateActiveCameraStateFromControls();
    return true;
  });

  loadKeyframes();
  if (activeKeyframeIndex !== null) {
    cameraSystem.setDirtyStateProvider(() => keyframes[activeKeyframeIndex]?.camera || null);
  }

  function openEditor(index) {
    if (!Number.isInteger(index) || index < 0 || index >= keyframes.length) return;
    if (!lightSystemRef || !settingsDialogEl) {
      selectKeyframe(index);
      return;
    }
    const frame = normalizeKeyframe(keyframes[index]);
    keyframes[index] = frame;
    if (!frame.lights) {
      frame.lights = lightSystemRef.getLightState();
    }

    isEditing = true;
    editingIndex = index;
    prevCameraState = cameraSystem.getCameraState();
    prevLightState = lightSystemRef.getLightState();

    activeKeyframeIndex = index;
    cameraSystem.setDirtyStateProvider(() => keyframes[activeKeyframeIndex]?.camera || null);
    cameraSystem.applyExternalCameraState(frame.camera);
    lightSystemRef.applyLightState(frame.lights);

    cameraSystem.syncCameraInputs();
    cameraSystem.renderCameraList();
    cameraSystem.updateCameraModeButton();
    lightSystemRef.syncLightInputs();
    lightSystemRef.renderDirectionalLightsList();

    if (settingsDialogEl) {
      if (!settingsTitleEl) {
        settingsTitleEl = settingsDialogEl.querySelector('.modal-header h3');
      }
      if (settingsTitleEl) {
        prevTitleText = settingsTitleEl.textContent;
        prevTitleDisplay = settingsTitleEl.style.display;
        settingsTitleEl.textContent = `Keyframe ${index + 1}`;
      }

      hiddenTabButtons = [];
      hiddenTabPanels = [];
      const tabButtons = settingsDialogEl.querySelectorAll('.tab-btn');
      const tabPanels = settingsDialogEl.querySelectorAll('.tab-panel');
      tabButtons.forEach((btn) => {
        if (btn.dataset.tab === 'general' || btn.dataset.tab === 'appearance') {
          hiddenTabButtons.push({ el: btn, display: btn.style.display });
          btn.style.display = 'none';
        }
      });
      tabPanels.forEach((panel) => {
        if (panel.dataset.tabPanel === 'general' || panel.dataset.tabPanel === 'appearance') {
          hiddenTabPanels.push({ el: panel, display: panel.style.display });
          panel.style.display = 'none';
        }
      });
    }

    if (cameraListEl) {
      prevCameraListDisplay = cameraListEl.style.display;
      cameraListEl.style.display = 'none';
    }
    if (addCameraBtnSettingsEl) {
      prevAddCameraDisplay = addCameraBtnSettingsEl.style.display;
      addCameraBtnSettingsEl.style.display = 'none';
    }
    if (removeCameraBtnSettingsEl) {
      prevRemoveCameraDisplay = removeCameraBtnSettingsEl.style.display;
      removeCameraBtnSettingsEl.style.display = 'none';
    }

    if (settingsSystemRef) {
      settingsSystemRef.activateTab('camera');
    }
    lightSystemRef.setDialogOpen(true);
    renderList();
  }

  function closeEditor() {
    exitKeyframeEditing({ restoreCamera: true, restoreLights: true, clearSelection: false, activateGlobalTab: false });
  }

  return {
    bindUI: ({
      panel,
      toggleButton,
      list,
      empty,
      addButton,
      removeButton,
      settingsDialog: dialog,
      settingsDialogClose: dialogClose,
      settingsSystem: settingsSys,
      lightSystem: lightsSys,
      cameraList,
      addCameraBtnSettings,
      removeCameraBtnSettings,
    }) => {
      panelEl = panel || panelEl;
      toggleBtn = toggleButton || toggleBtn;
      listEl = list || listEl;
      emptyEl = empty || emptyEl;
      addBtn = addButton || addBtn;
      removeBtn = removeButton || removeBtn;
      settingsDialogEl = dialog || settingsDialogEl;
      settingsDialogCloseBtn = dialogClose || settingsDialogCloseBtn;
      settingsSystemRef = settingsSys || settingsSystemRef;
      lightSystemRef = lightsSys || lightSystemRef;
      cameraListEl = cameraList || cameraListEl;
      addCameraBtnSettingsEl = addCameraBtnSettings || addCameraBtnSettingsEl;
      removeCameraBtnSettingsEl = removeCameraBtnSettings || removeCameraBtnSettingsEl;

      if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
          setPanelOpen(!isPanelOpen);
        });
      }

      if (addBtn) {
        addBtn.addEventListener('click', () => {
          addKeyframe();
        });
      }

      if (removeBtn) {
        removeBtn.addEventListener('click', () => {
          removeActiveKeyframe();
        });
      }

      if (settingsDialogCloseBtn) {
        settingsDialogCloseBtn.addEventListener('click', () => {
          closeEditor();
        });
      }

      if (settingsDialogEl) {
        settingsDialogEl.addEventListener('click', (event) => {
          if (event.target === settingsDialogEl) {
            closeEditor();
          }
        });
      }

      setPanelOpen(false);
      renderList();
      cameraSystem.setDirtyStateProvider(null);
    },
    setEditorDependencies: ({
      settingsDialog: dialog,
      settingsDialogClose: dialogClose,
      settingsSystem: settingsSys,
      lightSystem: lightsSys,
      cameraList,
      addCameraBtnSettings,
      removeCameraBtnSettings,
    }) => {
      settingsDialogEl = dialog || settingsDialogEl;
      settingsDialogCloseBtn = dialogClose || settingsDialogCloseBtn;
      settingsSystemRef = settingsSys || settingsSystemRef;
      lightSystemRef = lightsSys || lightSystemRef;
      cameraListEl = cameraList || cameraListEl;
      addCameraBtnSettingsEl = addCameraBtnSettings || addCameraBtnSettingsEl;
      removeCameraBtnSettingsEl = removeCameraBtnSettings || removeCameraBtnSettingsEl;
    },
    handleCameraSelectionChange: () => {
      const isHome = cameraSystem.isHomeMode();
      const hasSaved = !!cameraSystem.getActiveCameraState();
      if (isHome || hasSaved) {
        if (isEditing) {
          exitKeyframeEditing({ restoreCamera: false, restoreLights: true, clearSelection: true, activateGlobalTab: true });
        } else if (activeKeyframeIndex !== null) {
          clearSelection();
          if (settingsSystemRef) {
            settingsSystemRef.activateTab('general');
          }
        }
      }
    },
    addKeyframe,
    removeActiveKeyframe,
    selectKeyframe,
    clearSelection,
    getKeyframes: () => keyframes.slice(),
  };
}
