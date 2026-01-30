const KEYFRAME_STORAGE_KEY = 'openmfd_keyframes_v1';

export function createKeyframeSystem({
  cameraSystem,
  lightSystem = null,
  modelSelector = null,
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
  let duplicateBtn = null;
  let moveUpBtn = null;
  let moveDownBtn = null;
  let removeBtn = null;
  let playBtn = null;
  let playFromStartBtn = null;

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
  let globalModelSelectionBeforeKeyframe = null;
  let selectionListenerAttached = false;
  let isPlaying = false;
  let playbackTimer = null;
  let playbackIndex = 0;

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
      frame.models = modelSelector ? modelSelector.getSelectionSnapshot() : frame.models;
      keyframes[editingIndex] = frame;
      saveKeyframes();
      renderList();

      if (restoreCamera && prevCameraState) {
        cameraSystem.applyExternalCameraState(prevCameraState);
      }
      if (restoreLights && prevLightState && lightSystemRef) {
        lightSystemRef.applyLightState(prevLightState);
      }
      if (modelSelector && globalModelSelectionBeforeKeyframe) {
        modelSelector.applySelectionSnapshot(globalModelSelectionBeforeKeyframe);
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
      return { camera: cameraSystem.getCameraState(), lights: null, models: null, time: 0 };
    }
    if (raw.camera || raw.lights) {
      return {
        camera: raw.camera || raw,
        lights: raw.lights || null,
        models: raw.models || null,
        time: Number.isFinite(raw.time) ? raw.time : 0,
      };
    }
    if (raw.pos && raw.target) {
      return { camera: raw, lights: null, models: null, time: 0 };
    }
    return { camera: cameraSystem.getCameraState(), lights: null, models: null, time: 0 };
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
      btn.innerHTML = `Keyframe ${index + 1}`;
      if (index === activeKeyframeIndex) {
        btn.classList.add('is-active');
      }
      btn.addEventListener('click', () => {
        selectKeyframe(index);
      });

      const timeInput = document.createElement('input');
      timeInput.type = 'number';
      timeInput.className = 'keyframe-time-input';
      timeInput.min = '0';
      timeInput.step = '0.1';
      timeInput.value = Number.isFinite(state.time) ? state.time : 0;
      timeInput.title = 'Keyframe time (s)';
      timeInput.addEventListener('change', () => {
        const next = Number.parseFloat(timeInput.value);
        const safeValue = Number.isFinite(next) ? Math.max(0, next) : 0;
        const frame = normalizeKeyframe(keyframes[index]);
        frame.time = safeValue;
        keyframes[index] = frame;
        enforceKeyframeTimes();
        renderList();
        saveKeyframes();
      });

      row.appendChild(editBtn);
      row.appendChild(btn);
      row.appendChild(timeInput);
      listEl.appendChild(row);
    });
    updateEmptyState();
    const hasSelection = activeKeyframeIndex !== null && keyframes.length > 0;
    if (removeBtn) {
      removeBtn.disabled = !hasSelection;
    }
    if (duplicateBtn) {
      duplicateBtn.disabled = !hasSelection;
    }
    if (moveUpBtn) {
      moveUpBtn.disabled = !hasSelection || activeKeyframeIndex <= 0;
    }
    if (moveDownBtn) {
      moveDownBtn.disabled = !hasSelection || activeKeyframeIndex >= keyframes.length - 1;
    }
    if (playBtn) {
      playBtn.disabled = keyframes.length === 0;
    }
  }

  function enforceKeyframeTimes() {
    const minStep = 0.1;
    keyframes.forEach((frame, index) => {
      const normalized = normalizeKeyframe(frame);
      if (index === 0) {
        normalized.time = 0;
      } else {
        const prevTime = Number.isFinite(keyframes[index - 1]?.time)
          ? keyframes[index - 1].time
          : 0;
        const nextTime = Number.isFinite(normalized.time) ? normalized.time : prevTime + minStep;
        normalized.time = Math.max(prevTime + minStep, nextTime);
      }
      keyframes[index] = normalized;
    });
  }

  function updatePlayButton() {
    if (!playBtn) return;
    const icon = playBtn.querySelector('i');
    const label = playBtn.querySelector('span');
    if (isPlaying) {
      if (icon) {
        icon.classList.remove('fa-play');
        icon.classList.add('fa-pause');
      }
      if (label) label.textContent = 'Pause';
    } else {
      if (icon) {
        icon.classList.remove('fa-pause');
        icon.classList.add('fa-play');
      }
      if (label) label.textContent = 'Play';
    }
  }

  function clearPlaybackTimer() {
    if (playbackTimer) {
      clearTimeout(playbackTimer);
      playbackTimer = null;
    }
  }

  function stopPlayback() {
    if (!isPlaying) return;
    isPlaying = false;
    clearPlaybackTimer();
    updatePlayButton();
  }

  function getTimelineDuration() {
    if (keyframes.length < 2) return 1;
    const times = keyframes.map((frame) => Number.isFinite(frame?.time) ? frame.time : 0);
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    const duration = maxTime - minTime;
    return duration > 0 ? duration : 1;
  }

  function scheduleNextPlaybackStep() {
    if (!isPlaying || keyframes.length === 0) return;
    const currentIndex = playbackIndex;
    const nextIndex = currentIndex + 1;
    if (nextIndex >= keyframes.length) {
      stopPlayback();
      return;
    }
    const currentTime = Number.isFinite(keyframes[currentIndex]?.time)
      ? keyframes[currentIndex].time
      : 0;
    const nextTime = Number.isFinite(keyframes[nextIndex]?.time)
      ? keyframes[nextIndex].time
      : 0;
    let delay = nextTime - currentTime;
    if (!Number.isFinite(delay)) delay = 1;
    delay = Math.max(0.05, delay);
    playbackTimer = setTimeout(() => {
      playbackIndex = nextIndex;
      selectKeyframe(playbackIndex);
      scheduleNextPlaybackStep();
    }, delay * 1000);
  }

  function startPlayback() {
    if (keyframes.length === 0) return;
    if (isPlaying) return;
    isPlaying = true;
    playbackIndex = activeKeyframeIndex !== null ? activeKeyframeIndex : 0;
    selectKeyframe(playbackIndex);
    updatePlayButton();
    clearPlaybackTimer();
    scheduleNextPlaybackStep();
  }

  function startPlaybackFromBeginning() {
    if (keyframes.length === 0) return;
    if (isPlaying) {
      stopPlayback();
    }
    isPlaying = true;
    playbackIndex = 0;
    selectKeyframe(playbackIndex);
    updatePlayButton();
    clearPlaybackTimer();
    scheduleNextPlaybackStep();
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
    if (activeKeyframeIndex === null && modelSelector) {
      globalModelSelectionBeforeKeyframe = modelSelector.getSelectionSnapshot();
    }
    activeKeyframeIndex = index;
    const frame = normalizeKeyframe(keyframes[index]);
    keyframes[index] = frame;
    cameraSystem.setDirtyStateProvider(() => keyframes[activeKeyframeIndex]?.camera || null);
    cameraSystem.setSuppressActiveCameraHighlight(true);
    if (frame.camera) {
      cameraSystem.applyExternalCameraState(frame.camera);
    }
    if (frame.lights && lightSystemRef) {
      lightSystemRef.applyLightState(frame.lights);
    }
    if (frame.models && modelSelector) {
      modelSelector.applySelectionSnapshot(frame.models);
    }
    renderList();
    cameraSystem.refreshUpdateButton();
    saveKeyframes();
  }

  function clearSelection() {
    activeKeyframeIndex = null;
    cameraSystem.setDirtyStateProvider(null);
    cameraSystem.setSuppressActiveCameraHighlight(false);
    renderList();
    cameraSystem.refreshUpdateButton();
    if (globalLightStateBeforeKeyframe && lightSystemRef) {
      lightSystemRef.applyLightState(globalLightStateBeforeKeyframe);
    }
    globalLightStateBeforeKeyframe = null;
    if (globalModelSelectionBeforeKeyframe && modelSelector) {
      modelSelector.applySelectionSnapshot(globalModelSelectionBeforeKeyframe);
    }
    globalModelSelectionBeforeKeyframe = null;
    saveKeyframes();
  }

  function addKeyframe() {
    const state = cameraSystem.getCameraState();
    const lights = lightSystemRef ? lightSystemRef.getLightState() : null;
    const models = modelSelector ? modelSelector.getSelectionSnapshot() : null;
    const lastTime = keyframes.length
      ? Number.isFinite(keyframes[keyframes.length - 1]?.time)
        ? keyframes[keyframes.length - 1].time
        : 0
      : 0;
    keyframes.push({ camera: state, lights, models, time: lastTime + 1 });
    enforceKeyframeTimes();
    selectKeyframe(keyframes.length - 1);
    saveKeyframes();
  }

  function duplicateActiveKeyframe() {
    if (activeKeyframeIndex === null) return;
    if (activeKeyframeIndex < 0 || activeKeyframeIndex >= keyframes.length) return;
    const frame = normalizeKeyframe(keyframes[activeKeyframeIndex]);
    const copy = {
      camera: frame.camera ? JSON.parse(JSON.stringify(frame.camera)) : frame.camera,
      lights: frame.lights ? JSON.parse(JSON.stringify(frame.lights)) : frame.lights,
      models: frame.models ? JSON.parse(JSON.stringify(frame.models)) : frame.models,
      time: Number.isFinite(frame.time) ? frame.time : 0,
    };
    const insertIndex = activeKeyframeIndex + 1;
    keyframes.splice(insertIndex, 0, copy);
    enforceKeyframeTimes();
    selectKeyframe(insertIndex);
    saveKeyframes();
  }

  function moveActiveKeyframe(direction) {
    if (activeKeyframeIndex === null) return;
    const nextIndex = activeKeyframeIndex + direction;
    if (nextIndex < 0 || nextIndex >= keyframes.length) return;
    const temp = keyframes[activeKeyframeIndex];
    keyframes[activeKeyframeIndex] = keyframes[nextIndex];
    keyframes[nextIndex] = temp;
    activeKeyframeIndex = nextIndex;
    enforceKeyframeTimes();
    if (isPlaying) {
      playbackIndex = activeKeyframeIndex;
    }
    renderList();
    saveKeyframes();
  }

  function removeActiveKeyframe() {
    if (activeKeyframeIndex === null) return;
    if (activeKeyframeIndex < 0 || activeKeyframeIndex >= keyframes.length) return;
    keyframes.splice(activeKeyframeIndex, 1);
    enforceKeyframeTimes();
    if (keyframes.length === 0) {
      stopPlayback();
    } else if (isPlaying && playbackIndex >= keyframes.length) {
      playbackIndex = 0;
    }
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
    frame.models = modelSelector ? modelSelector.getSelectionSnapshot() : frame.models;
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
    if (!frame.models && modelSelector) {
      frame.models = modelSelector.getSelectionSnapshot();
    }

    isEditing = true;
    editingIndex = index;
    prevCameraState = cameraSystem.getCameraState();
    prevLightState = lightSystemRef.getLightState();

    activeKeyframeIndex = index;
    cameraSystem.setDirtyStateProvider(() => keyframes[activeKeyframeIndex]?.camera || null);
    cameraSystem.applyExternalCameraState(frame.camera);
    lightSystemRef.applyLightState(frame.lights);
    if (frame.models && modelSelector) {
      modelSelector.applySelectionSnapshot(frame.models);
    }

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
      duplicateButton,
      moveUpButton,
      moveDownButton,
      removeButton,
      playButton,
      playFromStartButton,
      settingsDialog: dialog,
      settingsDialogClose: dialogClose,
      settingsSystem: settingsSys,
      lightSystem: lightsSys,
      modelSelector: modelSelectorRef,
      cameraList,
      addCameraBtnSettings,
      removeCameraBtnSettings,
    }) => {
      panelEl = panel || panelEl;
      toggleBtn = toggleButton || toggleBtn;
      listEl = list || listEl;
      emptyEl = empty || emptyEl;
      addBtn = addButton || addBtn;
      duplicateBtn = duplicateButton || duplicateBtn;
      moveUpBtn = moveUpButton || moveUpBtn;
      moveDownBtn = moveDownButton || moveDownBtn;
      removeBtn = removeButton || removeBtn;
      playBtn = playButton || playBtn;
      playFromStartBtn = playFromStartButton || playFromStartBtn;
      settingsDialogEl = dialog || settingsDialogEl;
      settingsDialogCloseBtn = dialogClose || settingsDialogCloseBtn;
      settingsSystemRef = settingsSys || settingsSystemRef;
      lightSystemRef = lightsSys || lightSystemRef;
      modelSelector = modelSelectorRef || modelSelector;
      cameraListEl = cameraList || cameraListEl;
      addCameraBtnSettingsEl = addCameraBtnSettings || addCameraBtnSettingsEl;
      removeCameraBtnSettingsEl = removeCameraBtnSettings || removeCameraBtnSettingsEl;

      if (modelSelector && !selectionListenerAttached) {
        modelSelector.setSelectionChangeCallback((snapshot) => {
          if (activeKeyframeIndex === null) return;
          const frame = normalizeKeyframe(keyframes[activeKeyframeIndex]);
          frame.models = snapshot;
          keyframes[activeKeyframeIndex] = frame;
          saveKeyframes();
        });
        selectionListenerAttached = true;
      }

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

      if (duplicateBtn) {
        duplicateBtn.addEventListener('click', () => {
          duplicateActiveKeyframe();
        });
      }

      if (moveUpBtn) {
        moveUpBtn.addEventListener('click', () => {
          moveActiveKeyframe(-1);
        });
      }

      if (moveDownBtn) {
        moveDownBtn.addEventListener('click', () => {
          moveActiveKeyframe(1);
        });
      }

      if (playBtn) {
        playBtn.addEventListener('click', () => {
          if (isPlaying) {
            stopPlayback();
          } else {
            startPlayback();
          }
        });
        updatePlayButton();
      }

      if (playFromStartBtn) {
        playFromStartBtn.addEventListener('click', () => {
          startPlaybackFromBeginning();
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
      modelSelector: modelSelectorRef,
      cameraList,
      addCameraBtnSettings,
      removeCameraBtnSettings,
    }) => {
      settingsDialogEl = dialog || settingsDialogEl;
      settingsDialogCloseBtn = dialogClose || settingsDialogCloseBtn;
      settingsSystemRef = settingsSys || settingsSystemRef;
      lightSystemRef = lightsSys || lightSystemRef;
      modelSelector = modelSelectorRef || modelSelector;
      cameraListEl = cameraList || cameraListEl;
      addCameraBtnSettingsEl = addCameraBtnSettings || addCameraBtnSettingsEl;
      removeCameraBtnSettingsEl = removeCameraBtnSettings || removeCameraBtnSettingsEl;

      if (modelSelector && !selectionListenerAttached) {
        modelSelector.setSelectionChangeCallback((snapshot) => {
          if (activeKeyframeIndex === null) return;
          const frame = normalizeKeyframe(keyframes[activeKeyframeIndex]);
          frame.models = snapshot;
          keyframes[activeKeyframeIndex] = frame;
          saveKeyframes();
        });
        selectionListenerAttached = true;
      }
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
