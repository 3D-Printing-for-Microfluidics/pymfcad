import * as THREE from '../lib/three/three.module.js';

const KEYFRAME_STORAGE_KEY = 'openmfd_keyframes_v1';
const DEFAULT_HOLD_DURATION = 1;
const DEFAULT_TRANSITION_DURATION = 1;

export function createKeyframeSystem({
  cameraSystem,
  lightSystem = null,
  modelSelector = null,
  modelManager = null,
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
  let panelBodyEl = null;
  let listEl = null;
  let emptyEl = null;
  let addBtn = null;
  let moveUpBtn = null;
  let moveDownBtn = null;
  let removeBtn = null;
  let playBtn = null;
  let playFromStartBtn = null;
  let transitionMenuEl = null;
  let transitionMenuListEl = null;
  let modelSelectorContainerEl = null;
  let modelSelectorHostEl = null;
  let modelSelectorHomeParent = null;
  let modelSelectorHomeNextSibling = null;

  let settingsDialogEl = settingsDialog;
  let settingsDialogCloseBtn = settingsDialogClose;
  let settingsSystemRef = settingsSystem;
  let lightSystemRef = lightSystem;
  let modelManagerRef = modelManager;
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
  let playbackRaf = null;
  let playbackIndex = 0;
  let playbackSegment = null;
  let suppressModelSelectionSave = false;

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
    restoreModels = true,
    clearSelection = false,
    activateGlobalTab = false,
  } = {}) {
    if (!isEditing) return;

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
    if (restoreModels && modelSelector && globalModelSelectionBeforeKeyframe) {
      modelSelector.applySelectionSnapshot(globalModelSelectionBeforeKeyframe);
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
      return {
        camera: cameraSystem.getCameraState(),
        lights: null,
        models: null,
        holdDuration: DEFAULT_HOLD_DURATION,
        transitionDuration: DEFAULT_TRANSITION_DURATION,
        transitions: {},
      };
    }
    if (raw.camera || raw.lights) {
      return {
        camera: raw.camera || raw,
        lights: raw.lights || null,
        models: raw.models || null,
        holdDuration: Number.isFinite(raw.holdDuration) ? raw.holdDuration : DEFAULT_HOLD_DURATION,
        transitionDuration: Number.isFinite(raw.transitionDuration)
          ? raw.transitionDuration
          : DEFAULT_TRANSITION_DURATION,
        transitions: raw.transitions || {},
      };
    }
    if (raw.pos && raw.target) {
      return {
        camera: raw,
        lights: null,
        models: null,
        holdDuration: DEFAULT_HOLD_DURATION,
        transitionDuration: DEFAULT_TRANSITION_DURATION,
        transitions: {},
      };
    }
    return {
      camera: cameraSystem.getCameraState(),
      lights: null,
      models: null,
      holdDuration: DEFAULT_HOLD_DURATION,
      transitionDuration: DEFAULT_TRANSITION_DURATION,
      transitions: {},
    };
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
        const legacyFrames = parsed.keyframes;
        const hasLegacyTime = legacyFrames.some((frame) => Object.prototype.hasOwnProperty.call(frame, 'time'));
        const hasDurationFields = legacyFrames.some(
          (frame) => Object.prototype.hasOwnProperty.call(frame, 'holdDuration') || Object.prototype.hasOwnProperty.call(frame, 'transitionDuration')
        );
        if (hasLegacyTime && !hasDurationFields) {
          const times = legacyFrames.map((frame) => (Number.isFinite(frame?.time) ? frame.time : 0));
          const migrated = legacyFrames.map((frame, index) => {
            const transitionDelta = index < times.length - 1 ? Math.max(0, times[index + 1] - times[index]) : 0;
            return normalizeKeyframe({
              ...frame,
              holdDuration: 0,
              transitionDuration: transitionDelta,
              transitions: {},
            });
          });
          legacyFrames.forEach((frame, index) => {
            const transitions = frame?.transitions || null;
            if (!transitions || Object.keys(transitions).length === 0) return;
            const targetIndex = Math.max(0, index - 1);
            migrated[targetIndex].transitions = {
              ...migrated[targetIndex].transitions,
              ...transitions,
            };
          });
          keyframes = migrated;
        } else {
          keyframes = legacyFrames.map((frame) => normalizeKeyframe(frame));
        }
        enforceKeyframeDurations();
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
      row.dataset.keyframeIndex = String(index);

      const topRow = document.createElement('div');
      topRow.className = 'keyframe-row-line';

      const bottomRow = document.createElement('div');
      bottomRow.className = 'keyframe-row-line keyframe-row-line-secondary';

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
      const holdInput = document.createElement('input');
      holdInput.type = 'number';
      holdInput.className = 'keyframe-time-input';
      holdInput.min = '0';
      holdInput.step = '0.1';
      holdInput.value = Number.isFinite(state.holdDuration) ? state.holdDuration : 0;
      holdInput.title = 'Keyframe hold duration (s)';
      holdInput.addEventListener('change', () => {
        const next = Number.parseFloat(holdInput.value);
        const safeValue = Number.isFinite(next) ? Math.max(0, next) : 0;
        const frame = normalizeKeyframe(keyframes[index]);
        frame.holdDuration = safeValue;
        keyframes[index] = frame;
        enforceKeyframeDurations();
        renderList();
        saveKeyframes();
      });

      const spacer = document.createElement('div');
      spacer.className = 'keyframe-row-spacer';

      const transitionLabel = document.createElement('div');
      transitionLabel.className = 'keyframe-transition-label';
      transitionLabel.textContent = 'Transition';

      const transitionInput = document.createElement('input');
      transitionInput.type = 'number';
      transitionInput.className = 'keyframe-time-input keyframe-transition-input';
      transitionInput.min = '0';
      transitionInput.step = '0.1';
      transitionInput.value = Number.isFinite(state.transitionDuration) ? state.transitionDuration : 0;
      transitionInput.title = 'Transition duration (s)';
      if (index >= keyframes.length - 1) {
        transitionInput.value = '0';
        transitionInput.disabled = true;
      }
      transitionInput.addEventListener('change', () => {
        const next = Number.parseFloat(transitionInput.value);
        const safeValue = Number.isFinite(next) ? Math.max(0, next) : 0;
        const frame = normalizeKeyframe(keyframes[index]);
        frame.transitionDuration = safeValue;
        keyframes[index] = frame;
        enforceKeyframeDurations();
        renderList();
        saveKeyframes();
      });

      topRow.appendChild(editBtn);
      topRow.appendChild(btn);
      topRow.appendChild(holdInput);

      bottomRow.appendChild(spacer);
      bottomRow.appendChild(transitionLabel);
      bottomRow.appendChild(transitionInput);

      row.appendChild(topRow);
      row.appendChild(bottomRow);
      listEl.appendChild(row);
    });
    updateEmptyState();
    const hasSelection = activeKeyframeIndex !== null && keyframes.length > 0;
    if (removeBtn) {
      removeBtn.disabled = !hasSelection;
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
    if (!hasSelection && transitionMenuEl) {
      transitionMenuEl.style.display = 'none';
    }
    if (hasSelection && transitionMenuEl) {
      transitionMenuEl.style.display = '';
    }
  }

  function scrollToActiveKeyframe() {
    if (!listEl || activeKeyframeIndex === null) return;
    const row = listEl.querySelector(`[data-keyframe-index="${activeKeyframeIndex}"]`);
    if (!row) return;
    row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function stableStringify(value) {
    if (value === null || value === undefined) return String(value);
    if (typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) {
      return `[${value.map((item) => stableStringify(item)).join(',')}]`;
    }
    const keys = Object.keys(value).sort();
    const pairs = keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`);
    return `{${pairs.join(',')}}`;
  }

  function isEqual(a, b) {
    return stableStringify(a) === stableStringify(b);
  }

  function getChangedItems(index) {
    if (!Number.isInteger(index) || index < 0 || index >= keyframes.length) return [];
    const current = normalizeKeyframe(keyframes[index]);
    const next = index < keyframes.length - 1 ? normalizeKeyframe(keyframes[index + 1]) : null;

    const changed = [];
    const pushIfChanged = (key, label, currentValue, nextValue) => {
      if (!next) return;
      if (!isEqual(currentValue, nextValue)) {
        changed.push({ key, label });
      }
    };

    pushIfChanged('camera', 'Camera', current.camera, next?.camera);
    pushIfChanged('lights', 'Lighting', current.lights, next?.lights);
    pushIfChanged('models', 'Models', current.models, next?.models);
    return changed;
  }

  function renderTransitionMenu() {
    if (!transitionMenuListEl || activeKeyframeIndex === null) return;
    if (activeKeyframeIndex >= keyframes.length - 1) {
      transitionMenuListEl.innerHTML = '';
      const note = document.createElement('div');
      note.className = 'transition-item';
      note.textContent = 'No transition after the last keyframe.';
      transitionMenuListEl.appendChild(note);
      return;
    }
    transitionMenuListEl.innerHTML = '';
    const items = getChangedItems(activeKeyframeIndex);
    if (items.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'transition-item';
      empty.textContent = 'No changes detected.';
      transitionMenuListEl.appendChild(empty);
      return;
    }

    const frame = normalizeKeyframe(keyframes[activeKeyframeIndex]);
    frame.transitions = frame.transitions || {};
    keyframes[activeKeyframeIndex] = frame;

    const options = [
      { value: 'start', label: 'On start' },
      { value: 'middle', label: 'In middle' },
      { value: 'end', label: 'On end' },
      { value: 'linear', label: 'Linear' },
      { value: 's-curve', label: 'S-curve' },
    ];

    items.forEach(({ key, label }) => {
      const row = document.createElement('div');
      row.className = 'transition-item';

      const name = document.createElement('label');
      name.textContent = label;

      const select = document.createElement('select');
      const entry = getTransitionEntry(frame, key);
      const current = entry.type || 'linear';
      options.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        if (opt.value === current) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener('change', () => {
        const updated = normalizeKeyframe(keyframes[activeKeyframeIndex]);
        updated.transitions = updated.transitions || {};
        updated.transitions[key] = {
          type: select.value,
          curve: getPresetCurve(select.value),
        };
        keyframes[activeKeyframeIndex] = updated;
        saveKeyframes();
        renderTransitionMenu();
      });

      const curveWrap = document.createElement('div');
      curveWrap.className = 'transition-curve';
      const width = 160;
      const height = 80;
      const svgNS = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
      svg.setAttribute('width', String(width));
      svg.setAttribute('height', String(height));

      const axis = document.createElementNS(svgNS, 'path');
      axis.setAttribute('d', `M5 ${height - 5} L${width - 5} ${height - 5} M5 ${height - 5} L5 5`);
      axis.setAttribute('stroke', 'currentColor');
      axis.setAttribute('stroke-width', '1');
      axis.setAttribute('opacity', '0.3');
      axis.setAttribute('fill', 'none');
      svg.appendChild(axis);

      const curvePath = document.createElementNS(svgNS, 'path');
      curvePath.setAttribute('stroke', 'currentColor');
      curvePath.setAttribute('stroke-width', '2');
      curvePath.setAttribute('fill', 'none');
      svg.appendChild(curvePath);

      const handles = [];
      for (let i = 1; i <= 3; i += 1) {
        const handle = document.createElementNS(svgNS, 'circle');
        handle.setAttribute('r', '4');
        handle.setAttribute('fill', 'currentColor');
        svg.appendChild(handle);
        handles.push(handle);
      }

      const updateCurveSvg = (curve) => {
        const points = normalizeCurvePoints(curve, current);
        const plot = points.map((p) => {
          const x = 5 + p.x * (width - 10);
          const y = (height - 5) - clamp01(p.y) * (height - 10);
          return { x, y };
        });
        const isStep = current === 'start' || current === 'middle' || current === 'end';
        let segments = [];
        if (isStep) {
          const samples = 32;
          for (let i = 0; i <= samples; i += 1) {
            const t = i / samples;
            const y = evaluateTransition({ transitions: { temp: { type: current } } }, 'temp', t);
            const x = 5 + t * (width - 10);
            const py = (height - 5) - y * (height - 10);
            segments.push(`${i === 0 ? 'M' : 'L'}${x} ${py}`);
          }
        } else {
          const smooth = smoothCurvePoints(points, 3);
          segments = smooth.map((p, idx) => {
            const x = 5 + p.x * (width - 10);
            const y = (height - 5) - clamp01(p.y) * (height - 10);
            return `${idx === 0 ? 'M' : 'L'}${x} ${y}`;
          });
        }
        curvePath.setAttribute('d', segments.join(' '));
        handles.forEach((handle, idx) => {
          const pt = plot[idx + 1];
          handle.setAttribute('cx', String(pt.x));
          handle.setAttribute('cy', String(pt.y));
        });
      };

      const applyCurveChange = (midIndex, cx, cy) => {
        const updated = normalizeKeyframe(keyframes[activeKeyframeIndex]);
        updated.transitions = updated.transitions || {};
        const currentEntry = getTransitionEntry(updated, key);
        const base = normalizeCurvePoints(currentEntry.curve || getPresetCurve(currentEntry.type || 'linear'), currentEntry.type || 'linear');
        const nextPoints = base.map((p) => ({ x: p.x, y: p.y }));
        const idx = midIndex + 1;
        nextPoints[2].x = 0.5;
        if (idx === 1) {
          nextPoints[idx].x = clamp01(Math.min(cx, 0.5));
        } else if (idx === 3) {
          nextPoints[idx].x = clamp01(Math.max(cx, 0.5));
        }
        nextPoints[idx].y = clamp01(cy);
        updated.transitions[key] = {
          type: currentEntry.type || 'linear',
          curve: { points: nextPoints },
        };
        keyframes[activeKeyframeIndex] = updated;
        saveKeyframes();
        updateCurveSvg({ points: nextPoints });
      };

      const pickMidIndex = (px, points) => {
        const xs = [points[1].x, points[2].x, points[3].x];
        let best = 0;
        let bestDist = Infinity;
        xs.forEach((x, idx) => {
          const dist = Math.abs(px - x);
          if (dist < bestDist) {
            bestDist = dist;
            best = idx;
          }
        });
        return best;
      };

      const onPointer = (event) => {
        const rect = svg.getBoundingClientRect();
        const px = clamp01((event.clientX - rect.left - 5) / (rect.width - 10));
        const py = clamp01(1 - (event.clientY - rect.top - 5) / (rect.height - 10));
        const currentFrame = normalizeKeyframe(keyframes[activeKeyframeIndex]);
        const currentEntry = getTransitionEntry(currentFrame, key);
        const points = normalizeCurvePoints(currentEntry.curve || getPresetCurve(currentEntry.type || 'linear'), currentEntry.type || 'linear');
        const midIndex = pickMidIndex(px, points);
        applyCurveChange(midIndex, px, py);
      };

      let dragging = false;
      const isStepType = current === 'start' || current === 'middle' || current === 'end';
      svg.style.opacity = isStepType ? '0.6' : '1';
      svg.style.pointerEvents = isStepType ? 'none' : 'auto';

      svg.addEventListener('pointerdown', (event) => {
        if (isStepType) return;
        dragging = true;
        svg.setPointerCapture(event.pointerId);
        onPointer(event);
      });
      svg.addEventListener('pointermove', (event) => {
        if (!dragging || isStepType) return;
        onPointer(event);
      });
      svg.addEventListener('pointerup', (event) => {
        dragging = false;
        svg.releasePointerCapture(event.pointerId);
      });
      svg.addEventListener('pointerleave', () => {
        dragging = false;
      });

      const initialCurve = entry.curve || getPresetCurve(current);
      updateCurveSvg(initialCurve);

      curveWrap.appendChild(svg);

      row.appendChild(name);
      row.appendChild(select);
      row.appendChild(curveWrap);
      transitionMenuListEl.appendChild(row);
    });
  }

  function enforceKeyframeDurations() {
    keyframes.forEach((frame, index) => {
      const normalized = normalizeKeyframe(frame);
      normalized.holdDuration = Number.isFinite(normalized.holdDuration) ? Math.max(0, normalized.holdDuration) : 0;
      normalized.transitionDuration = Number.isFinite(normalized.transitionDuration)
        ? Math.max(0, normalized.transitionDuration)
        : 0;
      if (index >= keyframes.length - 1) {
        normalized.transitionDuration = 0;
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

  function clearPlaybackRaf() {
    if (playbackRaf) {
      cancelAnimationFrame(playbackRaf);
      playbackRaf = null;
    }
  }

  function stopPlayback() {
    if (!isPlaying) return;
    isPlaying = false;
    playbackSegment = null;
    clearPlaybackRaf();
    suppressModelSelectionSave = false;
    updatePlayButton();
  }

  function easeFor(type, t) {
    if (type === 's-curve') {
      return t * t * (3 - 2 * t);
    }
    return t;
  }

  function getTransitionType(frame, key) {
    const entry = frame?.transitions?.[key];
    if (!entry) return 'linear';
    if (typeof entry === 'string') return entry;
    return entry.type || 'linear';
  }

  function getTransitionEntry(frame, key) {
    const entry = frame?.transitions?.[key];
    if (!entry) return { type: 'linear', curve: null };
    if (typeof entry === 'string') return { type: entry, curve: null };
    return {
      type: entry.type || 'linear',
      curve: entry.curve || null,
    };
  }

  function getPresetCurve(type) {
    switch (type) {
      case 'start':
        return {
          points: [
            { x: 0, y: 0 },
            { x: 0.25, y: 0.9 },
            { x: 0.5, y: 1 },
            { x: 0.75, y: 1 },
            { x: 1, y: 1 },
          ],
        };
      case 'end':
        return {
          points: [
            { x: 0, y: 0 },
            { x: 0.25, y: 0 },
            { x: 0.5, y: 0 },
            { x: 0.75, y: 0.1 },
            { x: 1, y: 1 },
          ],
        };
      case 's-curve':
        return {
          points: [
            { x: 0, y: 0 },
            { x: 0.25, y: 0.1 },
            { x: 0.5, y: 0.5 },
            { x: 0.75, y: 0.9 },
            { x: 1, y: 1 },
          ],
        };
      case 'middle':
        return {
          points: [
            { x: 0, y: 0 },
            { x: 0.25, y: 0.1 },
            { x: 0.5, y: 0.6 },
            { x: 0.75, y: 0.9 },
            { x: 1, y: 1 },
          ],
        };
      case 'linear':
      default:
        return {
          points: [
            { x: 0, y: 0 },
            { x: 0.25, y: 0.25 },
            { x: 0.5, y: 0.5 },
            { x: 0.75, y: 0.75 },
            { x: 1, y: 1 },
          ],
        };
    }
  }

  function clamp01(value) {
    return Math.max(0, Math.min(1, value));
  }

  function catmullRom(p0, p1, p2, p3, t) {
    const t2 = t * t;
    const t3 = t2 * t;
    return 0.5 * (
      (2 * p1) +
      (-p0 + p2) * t +
      (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
      (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    );
  }

  function smoothCurvePoints(points, iterations = 2) {
    if (!Array.isArray(points) || points.length < 2) return points || [];
    let current = points.map((p) => ({ x: p.x, y: p.y }));
    for (let i = 0; i < iterations; i += 1) {
      const next = [current[0]];
      for (let j = 0; j < current.length - 1; j += 1) {
        const p0 = current[j];
        const p1 = current[j + 1];
        const q = { x: 0.75 * p0.x + 0.25 * p1.x, y: 0.75 * p0.y + 0.25 * p1.y };
        const r = { x: 0.25 * p0.x + 0.75 * p1.x, y: 0.25 * p0.y + 0.75 * p1.y };
        next.push(q, r);
      }
      next.push(current[current.length - 1]);
      current = next;
    }
    return current;
  }

  function normalizeCurvePoints(curve, type) {
    const fallback = getPresetCurve(type).points;
    if (!curve || !Array.isArray(curve.points) || curve.points.length !== 5) {
      return fallback.map((p) => ({ x: p.x, y: p.y }));
    }
    const normalized = curve.points.map((p, idx) => {
      if (typeof p === 'number') {
        return { x: fallback[idx].x, y: clamp01(p) };
      }
      return {
        x: Number.isFinite(p?.x) ? clamp01(p.x) : fallback[idx].x,
        y: Number.isFinite(p?.y) ? clamp01(p.y) : fallback[idx].y,
      };
    });
    normalized[0].x = 0;
    normalized[4].x = 1;
    normalized[2].x = 0.5;
    normalized[1].x = Math.min(normalized[1].x, normalized[2].x);
    normalized[3].x = Math.max(normalized[3].x, normalized[2].x);
    return normalized;
  }

  function evaluateTransition(frame, key, t) {
    const entry = getTransitionEntry(frame, key);
    if (entry.type === 'start') return t <= 0 ? 0 : 1;
    if (entry.type === 'middle') return t < 0.5 ? 0 : 1;
    if (entry.type === 'end') return t < 1 ? 0 : 1;

    const points = normalizeCurvePoints(entry.curve || getPresetCurve(entry.type), entry.type);
    const smoothPoints = smoothCurvePoints(points, 3);
    const xs = smoothPoints.map((p) => p.x);
    const values = smoothPoints.map((p) => p.y);
    const clampedT = clamp01(t);
    let idx = 0;
    for (let i = 0; i < xs.length - 1; i += 1) {
      if (clampedT >= xs[i] && clampedT <= xs[i + 1]) {
        idx = i;
        break;
      }
    }
    const x0 = xs[idx];
    const x1 = xs[idx + 1];
    const localT = x1 === x0 ? 0 : (clampedT - x0) / (x1 - x0);
    const p0 = values[Math.max(0, idx - 1)];
    const p1 = values[idx];
    const p2 = values[idx + 1];
    const p3 = values[Math.min(values.length - 1, idx + 2)];
    return clamp01(catmullRom(p0, p1, p2, p3, localT));
  }

  function interpolateCameraState(start, end, t) {
    const startPos = new THREE.Vector3(start.pos.x, start.pos.y, start.pos.z);
    const startTarget = new THREE.Vector3(start.target.x, start.target.y, start.target.z);
    const endPos = new THREE.Vector3(end.pos.x, end.pos.y, end.pos.z);
    const endTarget = new THREE.Vector3(end.target.x, end.target.y, end.target.z);

    const startDir = startPos.clone().sub(startTarget);
    const endDir = endPos.clone().sub(endTarget);
    const startDirLen = startDir.length();
    const endDirLen = endDir.length();
    if (startDirLen > 0) startDir.divideScalar(startDirLen);
    if (endDirLen > 0) endDir.divideScalar(endDirLen);
    const dir = startDir.clone().lerp(endDir, t);
    if (dir.length() > 0) dir.normalize();

    const target = startTarget.clone().lerp(endTarget, t);
    const startDist = startPos.distanceTo(startTarget);
    const endDist = endPos.distanceTo(endTarget);
    const dist = startDist + (endDist - startDist) * t;
    const pos = target.clone().add(dir.multiplyScalar(dist));

    return {
      pos: { x: pos.x, y: pos.y, z: pos.z },
      target: { x: target.x, y: target.y, z: target.z },
      roll: (start.roll || 0) + ((end.roll || 0) - (start.roll || 0)) * t,
      fov: (start.fov || 0) + ((end.fov || 0) - (start.fov || 0)) * t,
      mode: end.mode || start.mode || 'perspective',
      controlType: end.controlType || start.controlType || 'orbit',
    };
  }

  function getModelVisibilityFromSnapshot(snapshot, idx) {
    if (!snapshot || !snapshot.models) return false;
    const cb = document.getElementById(`glb_cb_${idx}`);
    if (!cb) return false;
    const checked = Object.prototype.hasOwnProperty.call(snapshot.models, cb.id)
      ? snapshot.models[cb.id]
      : cb.checked;
    const groups = (cb.dataset.groups || '').split('|').filter(Boolean);
    const groupsOn = groups.every((groupId) => {
      if (!snapshot.groups) return true;
      if (Object.prototype.hasOwnProperty.call(snapshot.groups, groupId)) {
        return snapshot.groups[groupId];
      }
      return true;
    });
    return !!checked && groupsOn;
  }

  function buildVisibilityMap(snapshot) {
    const map = new Map();
    const count = modelManagerRef ? modelManagerRef.getModelCount() : 0;
    for (let i = 0; i < count; i += 1) {
      map.set(i, getModelVisibilityFromSnapshot(snapshot, i));
    }
    return map;
  }

  function applyModelTransition(startSnapshot, endSnapshot, t, transitionFrame) {
    if (!modelManagerRef || !modelSelector) return;
    const easedT = evaluateTransition(transitionFrame, 'models', t);

    const startMap = buildVisibilityMap(startSnapshot);
    const endMap = buildVisibilityMap(endSnapshot);
    const overrides = new Map();
    const count = modelManagerRef.getModelCount();

    if (playbackSegment && !playbackSegment.modelsStartApplied) {
      suppressModelSelectionSave = true;
      modelSelector.applySelectionSnapshot(startSnapshot, { persist: false });
      suppressModelSelectionSave = false;
      playbackSegment.modelsStartApplied = true;
    }

    for (let i = 0; i < count; i += 1) {
      const startVisible = startMap.get(i);
      const endVisible = endMap.get(i);
      if (startVisible && !endVisible) {
        overrides.set(i, true);
        modelManagerRef.setModelOpacity(i, 1 - easedT);
      } else if (!startVisible && endVisible) {
        overrides.set(i, true);
        modelManagerRef.setModelOpacity(i, easedT);
      } else if (startVisible && endVisible) {
        modelManagerRef.setModelOpacity(i, 1);
      } else {
        modelManagerRef.setModelOpacity(i, 0);
      }
    }
    modelManagerRef.setVisibilityOverrides(overrides);
    if (t >= 1 && playbackSegment && !playbackSegment.modelsEndApplied) {
      suppressModelSelectionSave = true;
      modelSelector.applySelectionSnapshot(endSnapshot, { persist: false });
      modelManagerRef.clearVisibilityOverrides();
      for (let i = 0; i < count; i += 1) {
        modelManagerRef.setModelOpacity(i, 1);
      }
      suppressModelSelectionSave = false;
      playbackSegment.modelsEndApplied = true;
    }
  }

  function applyCameraTransition(startFrame, endFrame, t, transitionFrame) {
    const easedT = evaluateTransition(transitionFrame, 'camera', t);
    const interpolated = interpolateCameraState(startFrame.camera, endFrame.camera, easedT);
    cameraSystem.applyExternalCameraState(interpolated);
  }

  function applyLightingTransition(startFrame, endFrame, t, transitionFrame) {
    if (!lightSystemRef) return;
    const easedT = evaluateTransition(transitionFrame, 'lights', t);
    lightSystemRef.applyLightStateInterpolated(startFrame.lights, endFrame.lights, easedT);
  }

  function applyFrameState(frame, { persist = false } = {}) {
    if (frame.camera) {
      cameraSystem.applyExternalCameraState(frame.camera);
    }
    if (frame.lights && lightSystemRef) {
      lightSystemRef.applyLightState(frame.lights);
    }
    if (frame.models && modelSelector) {
      modelSelector.applySelectionSnapshot(frame.models, { persist });
    }
    if (modelManagerRef) {
      modelManagerRef.clearVisibilityOverrides();
      const count = modelManagerRef.getModelCount();
      for (let i = 0; i < count; i += 1) {
        modelManagerRef.setModelOpacity(i, 1);
      }
    }
  }

  function applyAtTime(timeMs) {
    if (!keyframes.length) return;
    const clamped = Math.max(0, Number.isFinite(timeMs) ? timeMs : 0);
    let elapsed = 0;
    const prevSuppress = suppressModelSelectionSave;
    suppressModelSelectionSave = true;

    const ensureFrameData = (frame) => {
      if (!frame.lights && lightSystemRef) {
        frame.lights = lightSystemRef.getLightState();
      }
      if (!frame.models && modelSelector) {
        frame.models = modelSelector.getSelectionSnapshot();
      }
      return frame;
    };

    for (let i = 0; i < keyframes.length; i += 1) {
      const frame = ensureFrameData(normalizeKeyframe(keyframes[i]));
      const holdMs = Math.max(0, (Number.isFinite(frame.holdDuration) ? frame.holdDuration : 0) * 1000);
      if (clamped <= elapsed + holdMs || i === keyframes.length - 1) {
        applyFrameState(frame, { persist: false });
        suppressModelSelectionSave = prevSuppress;
        return;
      }
      elapsed += holdMs;

      const transitionMs = Math.max(0, (Number.isFinite(frame.transitionDuration) ? frame.transitionDuration : 0) * 1000);
      if (i < keyframes.length - 1) {
        const nextFrame = ensureFrameData(normalizeKeyframe(keyframes[i + 1]));
        if (clamped <= elapsed + transitionMs) {
          const t = transitionMs <= 0 ? 1 : (clamped - elapsed) / transitionMs;
          applyCameraTransition(frame, nextFrame, t, frame);
          applyLightingTransition(frame, nextFrame, t, frame);
          applyModelTransition(frame.models, nextFrame.models, t, frame);
          suppressModelSelectionSave = prevSuppress;
          return;
        }
      }
      elapsed += transitionMs;
    }

    const lastFrame = ensureFrameData(normalizeKeyframe(keyframes[keyframes.length - 1]));
    applyFrameState(lastFrame, { persist: false });
    suppressModelSelectionSave = prevSuppress;
  }

  function startSegment(fromIndex, toIndex, nowMs) {
    const startFrame = normalizeKeyframe(keyframes[fromIndex]);
    const endFrame = normalizeKeyframe(keyframes[toIndex]);
    if (!startFrame.lights && lightSystemRef) {
      startFrame.lights = lightSystemRef.getLightState();
    }
    if (!endFrame.lights && lightSystemRef) {
      endFrame.lights = startFrame.lights;
    }
    if (!startFrame.models && modelSelector) {
      startFrame.models = modelSelector.getSelectionSnapshot();
    }
    if (!endFrame.models && modelSelector) {
      endFrame.models = startFrame.models;
    }
    const holdDuration = Number.isFinite(startFrame.holdDuration) ? Math.max(0, startFrame.holdDuration) : 0;
    const transitionDuration = Number.isFinite(startFrame.transitionDuration)
      ? Math.max(0, startFrame.transitionDuration)
      : 0;

    playbackSegment = {
      fromIndex,
      toIndex,
      startTimeMs: nowMs,
      holdDurationMs: holdDuration * 1000,
      transitionDurationMs: transitionDuration * 1000,
      phase: holdDuration > 0 ? 'hold' : 'transition',
      holdApplied: false,
      modelsStartApplied: false,
      modelsEndApplied: false,
    };

    selectKeyframe(fromIndex, { applyState: false });
  }

  function tickPlayback(nowMs) {
    if (!isPlaying || !playbackSegment) return;
    const { fromIndex, toIndex, startTimeMs, holdDurationMs, transitionDurationMs } = playbackSegment;
    const startFrame = normalizeKeyframe(keyframes[fromIndex]);
    const endFrame = normalizeKeyframe(keyframes[toIndex]);
    if (!startFrame.lights && lightSystemRef) {
      startFrame.lights = lightSystemRef.getLightState();
    }
    if (!endFrame.lights && lightSystemRef) {
      endFrame.lights = startFrame.lights;
    }
    if (!startFrame.models && modelSelector) {
      startFrame.models = modelSelector.getSelectionSnapshot();
    }
    if (!endFrame.models && modelSelector) {
      endFrame.models = startFrame.models;
    }
    if (playbackSegment.phase === 'hold') {
      if (!playbackSegment.holdApplied) {
        if (startFrame.camera) {
          cameraSystem.applyExternalCameraState(startFrame.camera);
        }
        if (startFrame.lights && lightSystemRef) {
          lightSystemRef.applyLightState(startFrame.lights);
        }
        if (startFrame.models && modelSelector) {
          modelSelector.applySelectionSnapshot(startFrame.models, { persist: false });
        }
        playbackSegment.holdApplied = true;
      }
      if (holdDurationMs <= 0 || nowMs - startTimeMs >= holdDurationMs) {
        playbackSegment.phase = 'transition';
        playbackSegment.startTimeMs = nowMs;
      } else {
        playbackRaf = requestAnimationFrame(tickPlayback);
        return;
      }
    }

    const elapsed = nowMs - playbackSegment.startTimeMs;
    const rawT = transitionDurationMs <= 0
      ? 1
      : Math.min(1, Math.max(0, elapsed / transitionDurationMs));

    applyCameraTransition(startFrame, endFrame, rawT, startFrame);
    applyLightingTransition(startFrame, endFrame, rawT, startFrame);
    applyModelTransition(startFrame.models, endFrame.models, rawT, startFrame);

    if (rawT >= 1) {
      playbackIndex = toIndex;
      selectKeyframe(playbackIndex, { applyState: false });
      scrollToActiveKeyframe();
      if (playbackIndex >= keyframes.length - 1) {
        stopPlayback();
        return;
      }
      startSegment(playbackIndex, playbackIndex + 1, nowMs);
    }

    playbackRaf = requestAnimationFrame(tickPlayback);
  }

  function startPlayback(fromStart = false) {
    if (keyframes.length === 0) return;
    if (isPlaying) return;
    isPlaying = true;
    suppressModelSelectionSave = true;
    playbackIndex = fromStart || activeKeyframeIndex === null ? 0 : activeKeyframeIndex;
    if (playbackIndex >= keyframes.length - 1) {
      selectKeyframe(playbackIndex);
      stopPlayback();
      return;
    }
    const nextIndex = Math.min(playbackIndex + 1, keyframes.length - 1);
    const nowMs = performance.now();
    startSegment(playbackIndex, nextIndex, nowMs);
    updatePlayButton();
    clearPlaybackRaf();
    playbackRaf = requestAnimationFrame(tickPlayback);
  }

  function startPlaybackFromBeginning() {
    if (isPlaying) {
      stopPlayback();
    }
    startPlayback(true);
  }

  function setPanelOpen(open) {
    isPanelOpen = !!open;
    if (panelEl) {
      panelEl.style.display = isPanelOpen ? '' : 'none';
    }
    if (panelBodyEl) {
      panelBodyEl.style.display = '';
    }
    if (toggleBtn) {
      toggleBtn.classList.toggle('is-active', isPanelOpen);
    }
    setModelSelectorLocation(isPanelOpen);
  }

  function setModelSelectorLocation(enabled) {
    if (!modelSelectorContainerEl) return;
    if (!modelSelectorHomeParent) {
      modelSelectorHomeParent = modelSelectorContainerEl.parentElement;
      modelSelectorHomeNextSibling = modelSelectorContainerEl.nextElementSibling;
    }
    if (enabled && modelSelectorHostEl) {
      if (modelSelectorContainerEl.parentElement !== modelSelectorHostEl) {
        modelSelectorHostEl.appendChild(modelSelectorContainerEl);
      }
      modelSelectorContainerEl.classList.add('is-in-dialog');
      const form = modelSelectorContainerEl.querySelector('form');
      if (form) form.style.display = '';
    } else if (!enabled && modelSelectorHomeParent) {
      if (modelSelectorContainerEl.parentElement !== modelSelectorHomeParent) {
        if (modelSelectorHomeNextSibling && modelSelectorHomeNextSibling.parentElement === modelSelectorHomeParent) {
          modelSelectorHomeParent.insertBefore(modelSelectorContainerEl, modelSelectorHomeNextSibling);
        } else {
          modelSelectorHomeParent.appendChild(modelSelectorContainerEl);
        }
      }
      modelSelectorContainerEl.classList.remove('is-in-dialog');
    }
  }

  function selectKeyframe(index, options = {}) {
    if (!Number.isInteger(index) || index < 0 || index >= keyframes.length) return;
    const applyState = options.applyState !== false;
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
    if (applyState) {
      if (frame.camera) {
        cameraSystem.applyExternalCameraState(frame.camera);
      }
      if (frame.lights && lightSystemRef) {
        lightSystemRef.applyLightState(frame.lights);
      }
      if (frame.models && modelSelector) {
        modelSelector.applySelectionSnapshot(frame.models);
      }
    }
    renderList();
    scrollToActiveKeyframe();
    cameraSystem.refreshUpdateButton();
    renderTransitionMenu();
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
    if (transitionMenuEl) {
      transitionMenuEl.style.display = 'none';
    }
    saveKeyframes();
  }

  function addKeyframe() {
    const state = cameraSystem.getCameraState();
    const lights = lightSystemRef ? lightSystemRef.getLightState() : null;
    const models = modelSelector ? modelSelector.getSelectionSnapshot() : null;
    keyframes.push({
      camera: state,
      lights,
      models,
      holdDuration: DEFAULT_HOLD_DURATION,
      transitionDuration: DEFAULT_TRANSITION_DURATION,
      transitions: {},
    });
    enforceKeyframeDurations();
    selectKeyframe(keyframes.length - 1);
    scrollToActiveKeyframe();
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
    enforceKeyframeDurations();
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
    enforceKeyframeDurations();
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
        if (btn.dataset.tab === 'keyframes' || btn.dataset.tab === 'keyframe-models') {
          hiddenTabButtons.push({ el: btn, display: btn.style.display });
          btn.style.display = '';
        }
      });
      tabPanels.forEach((panel) => {
        if (panel.dataset.tabPanel === 'general' || panel.dataset.tabPanel === 'appearance') {
          hiddenTabPanels.push({ el: panel, display: panel.style.display });
          panel.style.display = 'none';
        }
        if (panel.dataset.tabPanel === 'keyframes' || panel.dataset.tabPanel === 'keyframe-models') {
          hiddenTabPanels.push({ el: panel, display: panel.style.display });
          panel.style.display = '';
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
      settingsSystemRef.activateTab('keyframes');
    }
    lightSystemRef.setDialogOpen(true);
    renderList();
    renderTransitionMenu();
  }

  function closeEditor() {
    exitKeyframeEditing({ restoreCamera: false, restoreLights: false, restoreModels: false, clearSelection: false, activateGlobalTab: false });
  }

  return {
    bindUI: ({
      panel,
      toggleButton,
      panelBody,
      list,
      empty,
      addButton,
      moveUpButton,
      moveDownButton,
      removeButton,
      playButton,
      playFromStartButton,
      transitionMenu,
      transitionMenuList,
      modelSelectorContainer,
      modelSelectorHost,
      settingsDialog: dialog,
      settingsDialogClose: dialogClose,
      settingsSystem: settingsSys,
      lightSystem: lightsSys,
      modelSelector: modelSelectorRef,
      modelManager: modelManagerRefInput,
      cameraList,
      addCameraBtnSettings,
      removeCameraBtnSettings,
    }) => {
      panelEl = panel || panelEl;
      toggleBtn = toggleButton || toggleBtn;
      panelBodyEl = panelBody || panelBodyEl;
      listEl = list || listEl;
      emptyEl = empty || emptyEl;
      addBtn = addButton || addBtn;
      moveUpBtn = moveUpButton || moveUpBtn;
      moveDownBtn = moveDownButton || moveDownBtn;
      removeBtn = removeButton || removeBtn;
      playBtn = playButton || playBtn;
      playFromStartBtn = playFromStartButton || playFromStartBtn;
      transitionMenuEl = transitionMenu || transitionMenuEl;
      transitionMenuListEl = transitionMenuList || transitionMenuListEl;
      modelSelectorContainerEl = modelSelectorContainer || modelSelectorContainerEl;
      modelSelectorHostEl = modelSelectorHost || modelSelectorHostEl;
      settingsDialogEl = dialog || settingsDialogEl;
      settingsDialogCloseBtn = dialogClose || settingsDialogCloseBtn;
      settingsSystemRef = settingsSys || settingsSystemRef;
      lightSystemRef = lightsSys || lightSystemRef;
      modelSelector = modelSelectorRef || modelSelector;
      modelManagerRef = modelManagerRefInput || modelManagerRef;
      cameraListEl = cameraList || cameraListEl;
      addCameraBtnSettingsEl = addCameraBtnSettings || addCameraBtnSettingsEl;
      removeCameraBtnSettingsEl = removeCameraBtnSettings || removeCameraBtnSettingsEl;

      if (modelSelector && !selectionListenerAttached) {
        modelSelector.setSelectionChangeCallback((snapshot) => {
          if (activeKeyframeIndex === null || suppressModelSelectionSave) return;
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

      if (transitionMenuEl) {
        transitionMenuEl.style.display = activeKeyframeIndex === null ? 'none' : '';
        renderTransitionMenu();
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
      modelManager: modelManagerRefInput,
      cameraList,
      addCameraBtnSettings,
      removeCameraBtnSettings,
    }) => {
      settingsDialogEl = dialog || settingsDialogEl;
      settingsDialogCloseBtn = dialogClose || settingsDialogCloseBtn;
      settingsSystemRef = settingsSys || settingsSystemRef;
      lightSystemRef = lightsSys || lightSystemRef;
      modelSelector = modelSelectorRef || modelSelector;
      modelManagerRef = modelManagerRefInput || modelManagerRef;
      cameraListEl = cameraList || cameraListEl;
      addCameraBtnSettingsEl = addCameraBtnSettings || addCameraBtnSettingsEl;
      removeCameraBtnSettingsEl = removeCameraBtnSettings || removeCameraBtnSettingsEl;

      if (modelSelector && !selectionListenerAttached) {
        modelSelector.setSelectionChangeCallback((snapshot) => {
          if (activeKeyframeIndex === null || suppressModelSelectionSave) return;
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
          exitKeyframeEditing({ restoreCamera: false, restoreLights: true, restoreModels: true, clearSelection: true, activateGlobalTab: true });
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
    startPlaybackFromBeginning,
    stopPlayback,
    applyAtTime,
    getKeyframes: () => keyframes.slice(),
  };
}
