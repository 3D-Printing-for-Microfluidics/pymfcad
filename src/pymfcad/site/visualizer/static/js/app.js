import '@fortawesome/fontawesome-free/css/all.css';
import '../css/visualizer.css';

import { createScene } from './scene.js';
import { createModelManager } from './models.js';
import { createModelSelector } from './modelSelector.js';
import { createCameraSystem } from './camera.js';
import { createLightSystem } from './lights.js';
import { createPreviewSystem } from './preview.js';
import { createKeyframeSystem } from './keyframes.js';
import { createThemeManager } from './themes.js';
import { createSettingsSystem } from './settings.js';

const AUTO_RELOAD_STORAGE_KEY = 'pymfcad_auto_reload';
const AUTO_RELOAD_INTERVAL_KEY = 'pymfcad_auto_reload_interval_ms';
const AXES_STORAGE_KEY = 'pymfcad_axes_visible';
const DEFAULT_CONTROLS_TYPE_STORAGE_KEY = 'pymfcad_default_controls_type';
const MODEL_DEFAULT_VERSION_KEY = 'pymfcad_model_default_version';
const LIGHTS_STORAGE_KEY = 'pymfcad_lights_v1';
const MEASUREMENT_UNITS_KEY = 'pymfcad_measurement_units_v1';

const sceneState = createScene();
const {
  scene,
  world,
  axes,
  renderer,
  controls: initialControls,
  orbitControls,
  trackballControls,
  perspectiveCamera,
  orthographicCamera,
  setControlsType,
  THREE,
} = sceneState;
renderer.autoClear = false;
let controls = initialControls;

const modelManager = createModelManager({ scene, world });

let lightSystem = null;
let keyframeSystem = null;
const cameraSystem = createCameraSystem({
  scene,
  world,
  controls,
  perspectiveCamera,
  orthographicCamera,
  getFrameBox: modelManager.getFrameBox,
  getBoundingBoxScene: modelManager.getBoundingBoxScene,
  buildVisibleGroup: modelManager.buildVisibleGroup,
  onCameraChange: () => {
    if (previewSystem) {
      previewSystem.syncFromMain();
    }
  },
  onCameraModeChange: (mode) => {
    if (keyframeSystem?.applyCameraModeToKeyframes) {
      keyframeSystem.applyCameraModeToKeyframes(mode);
    }
  },
  onControlTypeChange: (type) => {
    applyControlsType(type, false);
    syncCameraControlSelect();
  },
  onActiveCameraChange: () => {
    syncCameraControlSelect();
    if (keyframeSystem) {
      keyframeSystem.handleCameraSelectionChange();
    }
  },
});

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const measurementPointerState = {
  isDown: false,
  startX: 0,
  startY: 0,
};
const measurementScene = new THREE.Scene();

const measurementGeometry = new THREE.BufferGeometry();
const measurementMaterial = new THREE.LineBasicMaterial({
  color: 0x4fd1c5,
  depthTest: false,
  depthWrite: false,
});
const measurementLine = new THREE.Line(measurementGeometry, measurementMaterial);
measurementLine.visible = false;
measurementLine.renderOrder = 1000;
measurementScene.add(measurementLine);

const measurementBeam = new THREE.Mesh(
  new THREE.CylinderGeometry(0.02, 0.02, 1, 16, 1, false),
  new THREE.MeshBasicMaterial({
    color: 0x4fd1c5,
    transparent: true,
    opacity: 0.95,
    depthTest: false,
    depthWrite: false,
  })
);
measurementBeam.visible = false;
measurementBeam.renderOrder = 1000;
measurementBeam.frustumCulled = false;
measurementScene.add(measurementBeam);

const measurementBeamAxis = new THREE.Vector3(0, 1, 0);

const measurementPointGeometry = new THREE.SphereGeometry(0.003, 100, 100);
const measurementStartMarker = new THREE.Mesh(
  measurementPointGeometry,
  new THREE.MeshBasicMaterial({ color: 0x4fd1c5, depthTest: false, depthWrite: false })
);
const measurementEndMarker = new THREE.Mesh(
  measurementPointGeometry,
  new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false, depthWrite: false })
);
measurementStartMarker.visible = false;
measurementEndMarker.visible = false;
measurementStartMarker.renderOrder = 1001;
measurementEndMarker.renderOrder = 1001;
measurementScene.add(measurementStartMarker);
measurementScene.add(measurementEndMarker);

const measurementState = {
  enabled: false,
  startPoint: null,
  endPoint: null,
};

const measurementPanel = document.getElementById('measurementPanel');
const measurementPanelToggleBtn = document.getElementById('measurementPanelToggleBtn');
const measurementToggleBtn = document.getElementById('measurementToggleBtn');
const measurementClearBtn = document.getElementById('measurementClearBtn');
const measurementReadout = document.getElementById('measurementReadout');
const measurementUnitsHost = document.getElementById('measurementUnitsHost');
let measurementUnitButtons = [];

const UNIT_FACTORS = {
  m: 0.001,
  cm: 0.1,
  mm: 1,
  'μm': 1000,
};

let measurementUnits = localStorage.getItem(MEASUREMENT_UNITS_KEY) || 'μm';

function setMeasurementUnits(units, { persist = true } = {}) {
  if (!units) return;
  measurementUnits = units;
  if (measurementUnitButtons && measurementUnitButtons.length) {
    measurementUnitButtons.forEach((btn) => {
      const isActive = btn.dataset.unit === units;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-pressed', String(isActive));
    });
  }
  if (persist) localStorage.setItem(MEASUREMENT_UNITS_KEY, units);
  if (measurementState.startPoint && measurementState.endPoint) {
    // Recompute readout with new units
    setMeasurementEnd(measurementState.endPoint);
  }
}

function initMeasurementUnitButtons() {
  if (!measurementUnitsHost) return;
  measurementUnitButtons = Array.from(measurementUnitsHost.querySelectorAll('.measurement-units-btn'));
  measurementUnitButtons.forEach((btn) => {
    const unit = btn.dataset.unit;
    btn.addEventListener('click', () => setMeasurementUnits(unit));
  });
  // reflect current selection without persisting
  setMeasurementUnits(measurementUnits, { persist: false });
}
initMeasurementUnitButtons();

function formatMeasurementPoint(point) {
  if (!point) return '(n/a)';
  return `(${point.x.toFixed(3)}, ${point.y.toFixed(3)}, ${point.z.toFixed(3)})`;
}

function updateMeasurementReadout(message, { html = false } = {}) {
  if (!measurementReadout) return;
  if (html) {
    measurementReadout.innerHTML = message;
  } else {
    measurementReadout.textContent = message;
  }
}

function setMeasurementButtonState(enabled) {
  if (!measurementToggleBtn) return;
  measurementToggleBtn.classList.toggle('is-active', enabled);
  measurementToggleBtn.textContent = `Measure: ${enabled ? 'On' : 'Off'}`;
  measurementToggleBtn.title = enabled
    ? 'Measurement mode active. Click two points on the model.'
    : 'Enable measurement mode.';
}

function clearMeasurement({ keepPrompt = false } = {}) {
  measurementState.startPoint = null;
  measurementState.endPoint = null;
  measurementStartMarker.visible = false;
  measurementEndMarker.visible = false;
  measurementLine.visible = false;
  measurementBeam.visible = false;
  measurementGeometry.setFromPoints([]);
  measurementScene.visible = false;
  if (measurementReadout && !keepPrompt) {
    updateMeasurementReadout(measurementState.enabled
      ? 'Click two points on the model.'
      : 'Measurement is off. Enable Measure to start.');
  }
}

function setMeasurementPanelVisible(visible) {
  if (!measurementPanel) return;
  measurementPanel.classList.toggle('is-hidden', !visible);
  if (measurementPanelToggleBtn) {
    measurementPanelToggleBtn.classList.toggle('is-active', visible);
    measurementPanelToggleBtn.title = visible ? 'Hide Measurement Pane' : 'Show Measurement Pane';
    measurementPanelToggleBtn.setAttribute('aria-pressed', String(visible));
  }
  if (!visible) {
    clearMeasurement();
    setMeasurementEnabled(false);
  }
}

function setMeasurementStart(point) {
  clearMeasurement({ keepPrompt: true });
  measurementState.startPoint = point.clone();
  measurementScene.visible = true;
  measurementStartMarker.position.copy(point);
  measurementStartMarker.visible = true;
  updateMeasurementReadout('Point A pinned. Select point B.');
}

function setMeasurementEnd(point) {
  if (!measurementState.startPoint) return;
  measurementState.endPoint = point.clone();
  measurementScene.visible = true;
  measurementEndMarker.position.copy(point);
  measurementEndMarker.visible = true;
  measurementLine.geometry.setFromPoints([measurementState.startPoint, measurementState.endPoint]);
  measurementLine.visible = true;
  const rawSegment = measurementState.endPoint.clone().sub(measurementState.startPoint);
  const segmentLength = rawSegment.length();
  if (segmentLength > 1e-6) {
    const segmentCenter = measurementState.startPoint.clone().add(measurementState.endPoint).multiplyScalar(0.5);
    measurementBeam.position.copy(segmentCenter);
    const beamDirection = rawSegment.clone().normalize();
    measurementBeam.quaternion.setFromUnitVectors(measurementBeamAxis, beamDirection);
    measurementBeam.scale.set(0.015, segmentLength, 0.015);
    measurementBeam.visible = true;
  } else {
    measurementBeam.visible = false;
  }
  const factor = UNIT_FACTORS[measurementUnits] || 1000000;
  const unitLabel = measurementUnits;
  const dxValue = Math.abs(rawSegment.x * factor);
  const dyValue = Math.abs(rawSegment.y * factor);
  const dzValue = Math.abs(rawSegment.z * factor);
  const totalValue = Math.sqrt(dxValue * dxValue + dyValue * dyValue + dzValue * dzValue);
  const dx = dxValue.toFixed(1);
  const dy = dyValue.toFixed(1);
  const dz = dzValue.toFixed(1);
  const total = totalValue.toFixed(1);
  const html = [
    `<div>A: ${formatMeasurementPoint(measurementState.startPoint)}</div>`,
    `<div>B: ${formatMeasurementPoint(measurementState.endPoint)}</div>`,
    `<div class="measurement-component measurement-dx">ΔX: <span class="measurement-value">${dx} ${unitLabel}</span></div>`,
    `<div class="measurement-component measurement-dy">ΔY: <span class="measurement-value">${dz} ${unitLabel}</span></div>`,
    `<div class="measurement-component measurement-dz">ΔZ: <span class="measurement-value">${dy} ${unitLabel}</span></div>`,
    `<div class="measurement-component measurement-total">Total: <span class="measurement-value">${total} ${unitLabel}</span></div>`,
  ].join('');
  updateMeasurementReadout(html, { html: true });
  showToast(`Measured total: ${total} ${unitLabel}`);
}

function setMeasurementEnabled(enabled) {
  measurementState.enabled = Boolean(enabled);
  setMeasurementButtonState(measurementState.enabled);
  renderer.domElement.style.cursor = measurementState.enabled ? 'crosshair' : 'default';
  if (!measurementState.enabled && measurementState.startPoint && !measurementState.endPoint) {
    clearMeasurement();
    return;
  }
  if (measurementState.enabled && !measurementState.startPoint) {
    updateMeasurementReadout('Click two points on the model.');
  } else if (!measurementState.enabled && !measurementState.startPoint) {
    updateMeasurementReadout('Measurement is off. Enable Measure to start.');
  }
}

function getRaycastHitFromEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  const camera = cameraSystem.getCamera();
  raycaster.setFromCamera(pointer, camera);
  const targetGroup = modelManager.buildVisibleGroup();
  if (!targetGroup) return null;
  targetGroup.matrixAutoUpdate = false;
  targetGroup.matrix.copy(world.matrixWorld);
  targetGroup.updateMatrixWorld(true);
  const hits = raycaster.intersectObject(targetGroup, true);
  return hits.find((entry) => entry.object?.isMesh) || null;
}

function handleMeasurementPick(event) {
  if (!measurementState.enabled) return;
  const hit = getRaycastHitFromEvent(event);
  if (!hit) return;
  if (!measurementState.startPoint || measurementState.endPoint) {
    setMeasurementStart(hit.point);
  } else {
    setMeasurementEnd(hit.point);
  }
}

renderer.domElement.addEventListener('pointerdown', (event) => {
  if (!measurementState.enabled || event.button !== 0) return;
  measurementPointerState.isDown = true;
  measurementPointerState.startX = event.clientX;
  measurementPointerState.startY = event.clientY;
});

renderer.domElement.addEventListener('pointerup', (event) => {
  if (!measurementState.enabled || event.button !== 0 || !measurementPointerState.isDown) return;
  measurementPointerState.isDown = false;
  const dx = Math.abs(event.clientX - measurementPointerState.startX);
  const dy = Math.abs(event.clientY - measurementPointerState.startY);
  if (dx > 6 || dy > 6) return;
  handleMeasurementPick(event);
});

renderer.domElement.addEventListener('pointercancel', () => {
  measurementPointerState.isDown = false;
});

renderer.domElement.addEventListener('dblclick', (event) => {
  if (measurementState.enabled) return;
  const hit = getRaycastHitFromEvent(event);
  if (!hit) return;

  const roll = cameraSystem.getCameraState().roll || 0;
  cameraSystem.setCameraPose(cameraSystem.getCamera().position.clone(), hit.point.clone(), roll);
});

keyframeSystem = createKeyframeSystem({ cameraSystem, modelManager });

const previewSystem = createPreviewSystem({
  scene,
  world,
  controls,
  cameraSystem,
  buildVisibleGroup: modelManager.buildVisibleGroup,
});

lightSystem = createLightSystem({
  scene,
  world,
  cameraSystem,
  previewSystem,
  getModelCenterModel: modelManager.getModelCenterModel,
});
if (lightSystem?.setLightStateChangeCallback) {
  lightSystem.setLightStateChangeCallback(() => {
    saveLightState();
    scheduleHistoryCapture();
  });
}

const modelSelector = createModelSelector({
  formEl: document.getElementById('glbForm'),
  toggleBtn: document.getElementById('toggleModelSelectorBtn'),
});

keyframeSystem.setEditorDependencies({
  modelSelector,
});

modelManager.setVisibilityResolver((idx) => modelSelector.getModelVisibility(idx));
modelSelector.setVisibilityCallback(() => {
  modelManager.updateVisibility();
  lightSystem.updateDirectionalLightTargets();
});
modelSelector.setVersionChangeCallback((idx, versionId) => {
  modelManager.setModelVersion(idx, versionId);
  lightSystem.updateDirectionalLightTargets();
});
modelSelector.setVersionChangeCallback((idx, versionId) => {
  modelManager.setModelVersion(idx, versionId);
});

const resetCameraBtn = document.getElementById('resetCameraBtn');
const reloadModelBtn = document.getElementById('reloadModelBtn');
const axesToggleBtn = document.getElementById('axesToggleBtn');

const cameraModeBtn = document.getElementById('cameraModeBtn');
const homeCameraBtn = document.getElementById('homeCameraBtn');
const centerTargetBtn = document.getElementById('centerTargetBtn');
const addCameraBtn = document.getElementById('addCameraBtn');
const addCameraBtnSettings = document.getElementById('addCameraBtnSettings');
const removeCameraBtnSettings = document.getElementById('removeCameraBtnSettings');
const camYaw = document.getElementById('camYaw');
const camPitch = document.getElementById('camPitch');
const camTargetX = document.getElementById('camTargetX');
const camTargetY = document.getElementById('camTargetY');
const camTargetZ = document.getElementById('camTargetZ');
const camDistance = document.getElementById('camDistance');
const camRoll = document.getElementById('camRoll');
const camFov = document.getElementById('camFov');
const defaultControlTypeSelect = document.getElementById('defaultControlTypeSelect');
const cameraControlTypeSelect = document.getElementById('cameraControlTypeSelect');
const cameraPresetButtons = Array.from(
  document.querySelectorAll('[data-camera-preset]')
);

const settingsDialogBtn = document.getElementById('settingsDialogBtn');
const settingsDialog = document.getElementById('settingsDialog');
const settingsDialogClose = document.getElementById('settingsDialogClose');
const docsBtn = document.getElementById('docsBtn');
const saveSnapshotBtn = document.getElementById('saveSnapshotBtn');
const animationToggleBtn = document.getElementById('animationToggleBtn');
const animationPanel = document.getElementById('animationPanel');
const animationPanelBody = document.getElementById('animationPanelBody');
const keyframeListEl = document.getElementById('keyframeList');
const keyframeEmptyEl = document.getElementById('keyframeEmpty');
const addKeyframeBtn = document.getElementById('addKeyframeBtn');
const moveKeyframeUpBtn = document.getElementById('moveKeyframeUpBtn');
const moveKeyframeDownBtn = document.getElementById('moveKeyframeDownBtn');
const removeKeyframeBtn = document.getElementById('removeKeyframeBtn');
const keyframePlayBtn = document.getElementById('keyframePlayBtn');
const keyframePlayFromStartBtn = document.getElementById('keyframePlayFromStartBtn');
const animationExportBtn = document.getElementById('animationExportBtn');
const transitionMenu = document.getElementById('transitionMenu');
const transitionMenuList = document.getElementById('transitionMenuList');
const updateCameraBtn = document.getElementById('updateCameraBtn');
const modelSelectorEl = document.getElementById('modelSelector');
const viewCubeEl = document.getElementById('viewCube');
const cameraStripWrapper = document.getElementById('cameraStripWrapper');
const controlsEl = document.getElementById('controls');
const settingsDialogEl = document.getElementById('settingsDialog');
const lightDialogViewer = document.getElementById('lightDialogViewer');
const lightsDialogViewer = document.getElementById('lightsDialogViewer');
const keyframeModelsViewer = document.getElementById('keyframeModelsViewer');
const keyframeModelSelectorHost = document.getElementById('keyframeModelSelectorHost');
const cameraListEl = document.getElementById('cameraList');
const cameraStripEl = document.getElementById('cameraStrip');
const ambientColorInput = document.getElementById('ambientColor');
const ambientIntensityInput = document.getElementById('ambientIntensity');
const directionalLightsList = document.getElementById('directionalLightsList');
const addDirLightBtn = document.getElementById('addDirLightBtn');
const removeDirLightBtn = document.getElementById('removeDirLightBtn');
const themeSelect = document.getElementById('themeSelect');
const themeResetBtn = document.getElementById('themeResetBtn');
const themeToCustomBtn = document.getElementById('themeToCustomBtn');
const themeInputs = {
  '--bg': document.getElementById('themeBg'),
  '--panel': document.getElementById('themePanel'),
  '--section-bg': document.getElementById('themeSection'),
  '--text': document.getElementById('themeText'),
  '--button-bg': document.getElementById('themeButtonBg'),
  '--button-text': document.getElementById('themeButtonText'),
  '--button-border': document.getElementById('themeButtonBorder'),
  '--button-bg-active': document.getElementById('themeButtonActive'),
  '--axis-x': document.getElementById('themeAxisX'),
  '--axis-y': document.getElementById('themeAxisY'),
  '--axis-z': document.getElementById('themeAxisZ'),
};
const cwdValueInput = document.getElementById('cwdValue');
const modelSourceValueInput = document.getElementById('modelSourceValue');
const previewDirInput = document.getElementById('previewDirInput');
const previewDirSetBtn = document.getElementById('previewDirSetBtn');
const previewDirResetBtn = document.getElementById('previewDirResetBtn');
const previewDirWarningEl = document.getElementById('previewDirWarning');
const autoReloadIntervalInput = document.getElementById('autoReloadIntervalInput');
const defaultModelVersionSelect = document.getElementById('defaultModelVersionSelect');
const resetSettingsSelect = document.getElementById('resetSettingsSelect');
const resetSettingsApplyBtn = document.getElementById('resetSettingsApplyBtn');
const settingsFileInput = document.getElementById('settingsFileInput');
const fileMenuBtn = document.getElementById('fileMenuBtn');
const editMenuBtn = document.getElementById('editMenuBtn');
const menuOpenBtn = document.getElementById('menuOpenBtn');
const menuSaveBtn = document.getElementById('menuSaveBtn');
const menuSaveSettingsBtn = document.getElementById('menuSaveSettingsBtn');
const menuLoadSettingsBtn = document.getElementById('menuLoadSettingsBtn');
const menuSettingsBtn = document.getElementById('menuSettingsBtn');
const menuUndoBtn = document.getElementById('menuUndoBtn');
const menuRedoBtn = document.getElementById('menuRedoBtn');
const previewSettingsDialog = document.getElementById('previewSettingsDialog');
const previewSettingsClose = document.getElementById('previewSettingsClose');
const previewSettingsFileSelect = document.getElementById('previewSettingsFileSelect');
const previewSettingsLoadBtn = document.getElementById('previewSettingsLoadBtn');
const previewSettingsFileInput = document.getElementById('previewSettingsFileInput');
const previewSettingsGeneral = document.getElementById('previewSettingsGeneral');
const previewSettingsTheme = document.getElementById('previewSettingsTheme');
const previewSettingsCamera = document.getElementById('previewSettingsCamera');
const previewSettingsLighting = document.getElementById('previewSettingsLighting');
const previewSettingsAnimation = document.getElementById('previewSettingsAnimation');
const toastEl = document.getElementById('toast');
const previewDirDialog = document.getElementById('previewDirDialog');
const previewDirClose = document.getElementById('previewDirClose');
const previewDirBaseInput = document.getElementById('previewDirBaseInput');
const previewDirRefreshBtn = document.getElementById('previewDirRefreshBtn');
const previewDirSelect = document.getElementById('previewDirSelect');
const previewDirCancelBtn = document.getElementById('previewDirCancelBtn');
const previewDirOpenBtn = document.getElementById('previewDirOpenBtn');
const snapshotDialog = document.getElementById('snapshotDialog');
const snapshotDialogClose = document.getElementById('snapshotDialogClose');
const snapshotSaveBtn = document.getElementById('snapshotSaveBtn');
const snapshotResolutionSelect = document.getElementById('snapshotResolution');
const snapshotProgress = document.getElementById('snapshotProgress');
const snapshotRendererSelect = document.getElementById('snapshotRenderer');
const snapshotPtPixelRatio = document.getElementById('snapshotPtPixelRatio');
const snapshotPtExposure = document.getElementById('snapshotPtExposure');
const snapshotPtSamples = document.getElementById('snapshotPtSamples');
const animationExportDialog = document.getElementById('animationExportDialog');
const animationExportClose = document.getElementById('animationExportClose');
const animationExportResolutionSelect = document.getElementById('animationExportResolution');
const animationExportFpsInput = document.getElementById('animationExportFps');
const animationExportQualitySelect = document.getElementById('animationExportQuality');
const animationExportTypeSelect = document.getElementById('animationExportType');
const animationExportSaveBtn = document.getElementById('animationExportSaveBtn');
const animationExportProgress = document.getElementById('animationExportProgress');
const animationRendererSelect = document.getElementById('animationRenderer');
const animationPtPixelRatio = document.getElementById('animationPtPixelRatio');
const animationPtExposure = document.getElementById('animationPtExposure');
const animationPtSamples = document.getElementById('animationPtSamples');

let settingsSystem = null;
let themeManager = null;
let pendingSettingsList = null;
const previewSettingsCustomFiles = new Map();
const previewSettingsCustomOrder = [];
let suppressLocalPersistence = false;
let skipBeforeUnloadSave = false;

function saveLightState() {
  if (suppressLocalPersistence || !lightSystem?.getLightState) return;
  const state = lightSystem.getLightState();
  if (!state) return;
  localStorage.setItem(LIGHTS_STORAGE_KEY, JSON.stringify(state));
}

function restorePersistedViewState() {
  suppressLocalPersistence = true;
  try {
    const lightRaw = localStorage.getItem(LIGHTS_STORAGE_KEY);
    if (lightRaw) {
      const lightState = JSON.parse(lightRaw);
      lightSystem.applyLightState(lightState);
    }
  } catch (e) {
    // ignore
  }
  suppressLocalPersistence = false;
}

function applyControlsType(type, persist = true) {
  const nextControls = setControlsType(type);
  if (!nextControls) return;
  controls = nextControls;
  cameraSystem.setControls(nextControls);
  previewSystem.setControls(nextControls);
  if (controls && controls.object) {
    controls.object = cameraSystem.getCamera();
  }
  cameraSystem.setRollEnabled(type === 'trackball');
  cameraSystem.setCurrentControlType(type);
  if (typeof controls.handleResize === 'function') {
    controls.handleResize();
  }
  if (persist) {
    localStorage.setItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY, type);
  }
}

function applyAxesState(visible) {
  axes.visible = !!visible;
  localStorage.setItem(AXES_STORAGE_KEY, String(axes.visible));
  if (axesToggleBtn) {
    axesToggleBtn.textContent = axes.visible ? 'Axes: On' : 'Axes: Off';
  }
}

function syncThemeInputs(themeName) {
  if (!themeManager || !themeInputs) return;
  const state = themeManager.getThemeState();
  const theme = state.themes?.[themeName];
  if (!theme) return;
  Object.entries(themeInputs).forEach(([key, input]) => {
    if (input) input.value = theme[key] || '#000000';
  });
}

function setSnapshotStatus(message) {
  if (!snapshotProgress) return;
  snapshotProgress.textContent = message || '';
}

let toastTimer = null;

const historyState = {
  undoStack: [],
  redoStack: [],
  isApplying: false,
  lastSerialized: null,
  captureTimer: null,
};

function getHistorySnapshot() {
  return {
    cameraState: cameraSystem?.getCameraState?.() || null,
    cameraStorage: localStorage.getItem('pymfcad_cameras_v1') || null,
    axesVisible: axes?.visible ?? true,
    defaultControlsType: cameraSystem?.getDefaultControlType?.() || defaultControlTypeSelect?.value || 'orbit',
    autoReloadEnabled,
    autoReloadIntervalMs,
    defaultModelVersion: getDefaultModelVersionStrategy(),
    modelSelection: modelSelector?.getSelectionSnapshot?.() || null,
    themeState: themeManager?.getThemeState?.() || null,
    lights: lightSystem?.getLightState?.() || null,
    keyframes: keyframeSystem?.getKeyframes?.() || [],
  };
}

function updateUndoRedoButtons() {
  if (menuUndoBtn) menuUndoBtn.disabled = historyState.undoStack.length === 0;
  if (menuRedoBtn) menuRedoBtn.disabled = historyState.redoStack.length === 0;
}

function pushHistorySnapshot() {
  if (historyState.isApplying) return;
  const snapshot = getHistorySnapshot();
  const serialized = JSON.stringify(snapshot);
  if (serialized === historyState.lastSerialized) return;
  historyState.undoStack.push(snapshot);
  if (historyState.undoStack.length > 100) {
    historyState.undoStack.shift();
  }
  historyState.redoStack = [];
  historyState.lastSerialized = serialized;
  updateUndoRedoButtons();
}

function scheduleHistoryCapture() {
  if (historyState.isApplying) return;
  if (historyState.captureTimer) window.clearTimeout(historyState.captureTimer);
  historyState.captureTimer = window.setTimeout(() => {
    historyState.captureTimer = null;
    pushHistorySnapshot();
  }, 250);
}

function applyHistorySnapshot(snapshot) {
  if (!snapshot) return;
  historyState.isApplying = true;
  if (snapshot.cameraStorage !== null) {
    localStorage.setItem('pymfcad_cameras_v1', snapshot.cameraStorage);
  } else {
    localStorage.removeItem('pymfcad_cameras_v1');
  }
  cameraSystem.initCameraStates();
  if (snapshot.cameraState) {
    cameraSystem.applyExternalCameraState(snapshot.cameraState);
  } else {
    cameraSystem.resetCameraHome();
  }
  syncCameraControlSelect();

  if (typeof snapshot.axesVisible === 'boolean') {
    applyAxesState(snapshot.axesVisible);
  }
  if (snapshot.defaultControlsType) {
    if (defaultControlTypeSelect) {
      defaultControlTypeSelect.value = snapshot.defaultControlsType;
    }
    cameraSystem.setDefaultControlType(snapshot.defaultControlsType);
    if (cameraSystem.isHomeMode() || !cameraSystem.getActiveCameraState()) {
      applyControlsType(snapshot.defaultControlsType, false);
    }
  }
  if (Number.isFinite(snapshot.autoReloadIntervalMs)) {
    setAutoReloadIntervalMs(snapshot.autoReloadIntervalMs);
    if (autoReloadIntervalInput) autoReloadIntervalInput.value = String(snapshot.autoReloadIntervalMs);
  }
  if (snapshot.autoReloadEnabled !== undefined) {
    autoReloadEnabled = !!snapshot.autoReloadEnabled;
    setAutoReload(autoReloadEnabled);
  }
  if (snapshot.defaultModelVersion) {
    if (defaultModelVersionSelect) {
      defaultModelVersionSelect.value = snapshot.defaultModelVersion;
    }
    setDefaultModelVersionStrategy(snapshot.defaultModelVersion);
    modelManager.applyDefaultVersionStrategy();
  }
  if (snapshot.modelSelection && modelSelector) {
    modelSelector.applySelectionSnapshot(snapshot.modelSelection, { persist: true });
    if (modelManager?.setModelVersionSelections) {
      modelManager.setModelVersionSelections(snapshot.modelSelection?.versions, { force: true });
    }
    modelManager.updateVisibility();
  }
  if (snapshot.themeState && themeManager) {
    themeManager.setThemeState(snapshot.themeState);
    if (themeSelect) {
      themeSelect.value = snapshot.themeState.activeTheme || themeSelect.value;
      syncThemeInputs(themeSelect.value);
    }
  }
  if (snapshot.lights && lightSystem) {
    lightSystem.applyLightState(snapshot.lights);
  }
  if (keyframeSystem?.setKeyframes && Array.isArray(snapshot.keyframes)) {
    keyframeSystem.setKeyframes(snapshot.keyframes);
  }
  historyState.isApplying = false;
}

function undoHistory() {
  if (historyState.undoStack.length === 0) return;
  const current = getHistorySnapshot();
  historyState.redoStack.push(current);
  const prev = historyState.undoStack.pop();
  historyState.lastSerialized = JSON.stringify(prev);
  applyHistorySnapshot(prev);
  updateUndoRedoButtons();
}

function redoHistory() {
  if (historyState.redoStack.length === 0) return;
  const current = getHistorySnapshot();
  historyState.undoStack.push(current);
  const next = historyState.redoStack.pop();
  historyState.lastSerialized = JSON.stringify(next);
  applyHistorySnapshot(next);
  updateUndoRedoButtons();
}

function showToast(message, { variant = 'info', duration = 2200 } = {}) {
  if (!toastEl) return;
  toastEl.textContent = message || '';
  toastEl.classList.toggle('is-error', variant === 'error');
  toastEl.classList.add('is-visible');
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toastEl.classList.remove('is-visible');
  }, duration);
}

function getDefaultModelVersionStrategy() {
  return localStorage.getItem(MODEL_DEFAULT_VERSION_KEY) || 'largest';
}

function setDefaultModelVersionStrategy(value) {
  const next = value === 'smallest' ? 'smallest' : 'largest';
  localStorage.setItem(MODEL_DEFAULT_VERSION_KEY, next);
  modelManager.setDefaultVersionStrategy(next);
}

function setAnimationExportStatus(message) {
  if (!animationExportProgress) return;
  animationExportProgress.textContent = message || '';
}

function applyAnimationSettingsPayload(payload) {
  if (!payload || typeof payload !== 'object') return;
  const exportDefaults = payload.exportDefaults || payload.export || null;
  if (exportDefaults) {
    const { resolution, fps, quality, type } = exportDefaults;
    if (resolution && animationExportResolutionSelect) animationExportResolutionSelect.value = resolution;
    if (Number.isFinite(fps) && animationExportFpsInput) animationExportFpsInput.value = String(fps);
    if (quality && animationExportQualitySelect) animationExportQualitySelect.value = quality;
    if (type && animationExportTypeSelect) animationExportTypeSelect.value = type;
    syncAnimationExportTypeForQuality();
  }
  if (Array.isArray(payload.keyframes) && keyframeSystem) {
    keyframeSystem.setKeyframes(payload.keyframes);
  }
}

function normalizeSnapshotName(name) {
  return 'pymfcad-viewport.png';
}

function getSnapshotSettings() {
  const fileName = normalizeSnapshotName();
  const resolutionValue = snapshotResolutionSelect?.value || 'current';
  let baseWidth = window.innerWidth;
  let baseHeight = window.innerHeight;
  if (resolutionValue && resolutionValue !== 'current') {
    const [w, h] = resolutionValue.split('x').map((value) => Number.parseInt(value, 10));
    if (Number.isFinite(w) && w > 0) baseWidth = w;
    if (Number.isFinite(h) && h > 0) baseHeight = h;
  }
  return {
    fileName,
    baseWidth,
    baseHeight,
    renderer: snapshotRendererSelect?.value || 'raster',
  };
}

function normalizeAnimationName(name, type) {
  const trimmed = (name || '').trim() || 'pymfcad-animation';
  const extMap = {
    webm: '.webm',
    mp4: '.mp4',
    gif: '.gif',
    avi: '.avi',
  };
  const ext = extMap[type] || '.webm';
  return trimmed.toLowerCase().endsWith(ext) ? trimmed : `${trimmed}${ext}`;
}

function getAnimationExportSettings() {
  const fps = Math.max(1, Math.min(60, Number.parseInt(animationExportFpsInput?.value || '30', 10) || 30));
  const quality = animationExportQualitySelect?.value || 'medium';
  let type = animationExportTypeSelect?.value || 'webm';
  if (quality === 'lossless') {
    type = 'webm';
    if (animationExportTypeSelect) {
      animationExportTypeSelect.value = 'webm';
    }
  }
  const fileName = normalizeAnimationName('', type);
  const resolutionValue = animationExportResolutionSelect?.value || '';
  const [w, h] = resolutionValue.split('x').map((value) => Number.parseInt(value, 10));
  const width = Number.isFinite(w) && w > 0 ? w : window.innerWidth;
  const height = Number.isFinite(h) && h > 0 ? h : window.innerHeight;
  return {
    width,
    height,
    fps,
    quality,
    type,
    fileName,
    renderer: animationRendererSelect?.value || 'raster',
  };
}

function syncAnimationExportTypeForQuality() {
  if (!animationExportQualitySelect || !animationExportTypeSelect) return;
  const isLossless = animationExportQualitySelect.value === 'lossless';
  const options = Array.from(animationExportTypeSelect.options);
  options.forEach((opt) => {
    if (opt.value !== 'webm') {
      opt.disabled = isLossless;
    }
  });
  if (isLossless) {
    animationExportTypeSelect.value = 'webm';
  }
}

function openSnapshotDialog() {
  if (!snapshotDialog) return;
  if (snapshotResolutionSelect) {
    const currentOption = Array.from(snapshotResolutionSelect.options)
      .find((option) => option.value === 'current');
    if (currentOption) {
      currentOption.textContent = `Current (${window.innerWidth}×${window.innerHeight})`;
    }
  }
  setSnapshotStatus('');
  snapshotDialog.classList.add('is-open');
}

function closeSnapshotDialog() {
  if (!snapshotDialog) return;
  snapshotDialog.classList.remove('is-open');
  setSnapshotStatus('');
}

function openAnimationExportDialog() {
  if (!animationExportDialog) return;
  setAnimationExportStatus('');
  animationExportDialog.classList.add('is-open');
}

function closeAnimationExportDialog() {
  if (!animationExportDialog) return;
  animationExportDialog.classList.remove('is-open');
  setAnimationExportStatus('');
}

async function saveBlobAsFile(blob, fileName) {
  if (!blob) return;
  if ('showSaveFilePicker' in window) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [
          {
            description: 'PNG Image',
            accept: { 'image/png': ['.png'] },
          },
        ],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    } catch (err) {
      if (err && err.name === 'AbortError') {
        return;
      }
      // fall back to download link
    }
  }

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function renderRasterSnapshot({ width, height }) {
  const offscreenCanvas = document.createElement('canvas');
  const offscreenRenderer = new THREE.WebGLRenderer({ canvas: offscreenCanvas, antialias: true, preserveDrawingBuffer: true });
  offscreenRenderer.setSize(width, height, false);
  offscreenRenderer.setPixelRatio(1);
  offscreenRenderer.outputColorSpace = renderer.outputColorSpace;
  offscreenRenderer.toneMapping = renderer.toneMapping;
  offscreenRenderer.toneMappingExposure = renderer.toneMappingExposure;

  const activeCamera = cameraSystem.getCamera();
  const snapshotCamera = activeCamera.clone();
  snapshotCamera.matrixWorld.copy(activeCamera.matrixWorld);
  snapshotCamera.matrixWorldInverse.copy(activeCamera.matrixWorldInverse);

  if (snapshotCamera.isPerspectiveCamera) {
    snapshotCamera.aspect = width / height;
    snapshotCamera.updateProjectionMatrix();
  } else if (snapshotCamera.isOrthographicCamera) {
    const centerX = (snapshotCamera.left + snapshotCamera.right) / 2;
    const centerY = (snapshotCamera.top + snapshotCamera.bottom) / 2;
    const viewHeight = snapshotCamera.top - snapshotCamera.bottom;
    const viewWidth = viewHeight * (width / height);
    snapshotCamera.left = centerX - viewWidth / 2;
    snapshotCamera.right = centerX + viewWidth / 2;
    snapshotCamera.top = centerY + viewHeight / 2;
    snapshotCamera.bottom = centerY - viewHeight / 2;
    snapshotCamera.updateProjectionMatrix();
  }

  offscreenRenderer.render(scene, snapshotCamera);

  const blob = await new Promise((resolve) => offscreenCanvas.toBlob(resolve, 'image/png'));
  offscreenRenderer.dispose();
  if (!blob) return null;
  return blob;
}

async function handleSnapshotSave() {
  const settings = getSnapshotSettings();
  const baseWidth = settings.baseWidth;
  const baseHeight = settings.baseHeight;
  const maxPixels = 3840 * 2160;
  const pixelCount = baseWidth * baseHeight;
  let exportWidth = baseWidth;
  let exportHeight = baseHeight;
  if (pixelCount > maxPixels) {
    const scale = Math.sqrt(maxPixels / pixelCount);
    exportWidth = Math.max(1, Math.round(baseWidth * scale));
    exportHeight = Math.max(1, Math.round(baseHeight * scale));
    setSnapshotStatus(`Resolution reduced to ${exportWidth}×${exportHeight} to avoid memory issues.`);
  }
  const uiElements = [modelSelectorEl, cameraStripWrapper, controlsEl, settingsDialogEl].filter(Boolean);
  const prevCameraHelperVisible = typeof cameraSystem.getCameraHelperVisible === 'function'
    ? cameraSystem.getCameraHelperVisible()
    : false;
  uiElements.forEach((el) => el.classList.add('ui-hidden'));
  if (snapshotSaveBtn) snapshotSaveBtn.disabled = true;
  if (snapshotDialogClose) snapshotDialogClose.disabled = true;
  setSnapshotStatus('Rendering snapshot...');
  cameraSystem.setCameraHelperVisible(false);

  try {
    let blob = null;
    const renderWidth = exportWidth;
    const renderHeight = exportHeight;
    let saveHandle = null;
    blob = await renderRasterSnapshot({ width: renderWidth, height: renderHeight });

    if (!blob) {
      setSnapshotStatus('Snapshot failed to render.');
      return;
    }
    setSnapshotStatus('Saving...');
    if (saveHandle) {
      const writable = await saveHandle.createWritable();
      await writable.write(blob);
      await writable.close();
    } else {
      await saveBlobAsFile(blob, settings.fileName);
    }
    closeSnapshotDialog();
  } catch (err) {
    console.log('Snapshot save error:', err);
    const message = err instanceof Error ? err.message : 'Snapshot failed.';
    setSnapshotStatus(message);
  } finally {
    uiElements.forEach((el) => el.classList.remove('ui-hidden'));
    if (snapshotSaveBtn) snapshotSaveBtn.disabled = false;
    if (snapshotDialogClose) snapshotDialogClose.disabled = false;
    cameraSystem.setCameraHelperVisible(prevCameraHelperVisible);
  }
}

function getAnimationDurationMs() {
  if (!keyframeSystem) return 0;
  const frames = keyframeSystem.getKeyframes();
  if (!frames.length) return 0;
  const minDuration = 0.05;
  return frames.reduce((total, frame, index) => {
    const hold = Number.isFinite(frame?.holdDuration)
      ? Math.max(minDuration, frame.holdDuration)
      : minDuration;
    const transition = index >= frames.length - 1
      ? 0
      : (Number.isFinite(frame?.transitionDuration)
        ? Math.max(0, frame.transitionDuration)
        : 0);
    return total + (hold + transition) * 1000;
  }, 0);
}

function applyExportCameraSize(width, height) {
  const camera = cameraSystem.getCamera();
  if (!camera) return;
  if (camera.isPerspectiveCamera) {
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  } else if (camera.isOrthographicCamera) {
    const centerX = (camera.left + camera.right) / 2;
    const centerY = (camera.top + camera.bottom) / 2;
    const viewHeight = camera.top - camera.bottom;
    const viewWidth = viewHeight * (width / height);
    camera.left = centerX - viewWidth / 2;
    camera.right = centerX + viewWidth / 2;
    camera.top = centerY + viewHeight / 2;
    camera.bottom = centerY - viewHeight / 2;
    camera.updateProjectionMatrix();
  }
}

async function handleAnimationExport() {
  if (!animationExportSaveBtn || !animationExportClose) return;
  const settings = getAnimationExportSettings();
  const durationMs = getAnimationDurationMs();
  if (!durationMs) {
    setAnimationExportStatus('Add keyframes before exporting.');
    return;
  }
  if (!renderer?.domElement?.captureStream || typeof MediaRecorder === 'undefined') {
    setAnimationExportStatus('Recording is not supported in this browser.');
    return;
  }

  let exportRenderer = null;
  const prevCameraHelperVisible = typeof cameraSystem.getCameraHelperVisible === 'function'
    ? cameraSystem.getCameraHelperVisible()
    : false;
  const prevCameraState = cameraSystem.getCameraState();
  const prevLightState = lightSystem ? lightSystem.getLightState() : null;
  const prevModelSelection = modelSelector ? modelSelector.getSelectionSnapshot() : null;

  const exportWidth = Math.max(1, Math.round(settings.width));
  const exportHeight = Math.max(1, Math.round(settings.height));
  let effectiveFps = settings.fps;
  if (settings.quality === 'lossless' && effectiveFps > 30) {
    effectiveFps = 30;
    setAnimationExportStatus('Lossless export capped at 30 fps to avoid memory issues.');
  }
  if (settings.quality === 'lossless' && exportWidth * exportHeight * effectiveFps > 3840 * 2160 * 30) {
    setAnimationExportStatus('Lossless export at this resolution/fps is too heavy. Lower resolution or fps.');
    return;
  }
  const uiElements = [modelSelectorEl, cameraStripWrapper, controlsEl, settingsDialogEl, animationPanel].filter(Boolean);

  const prevSize = new THREE.Vector2();
  renderer.getSize(prevSize);
  const prevPixelRatio = renderer.getPixelRatio();

  uiElements.forEach((el) => el.classList.add('ui-hidden'));
  cameraSystem.setCameraHelperVisible(false);
  animationExportSaveBtn.disabled = true;
  animationExportClose.disabled = true;
  setAnimationExportStatus('Recording animation...');

  try {
    renderer.setPixelRatio(1);
    applyExportCameraSize(exportWidth, exportHeight);

    let mimeType = '';
    let videoBitsPerSecond = 12000000;
    if (settings.quality === 'low') {
      videoBitsPerSecond = 4000000;
    } else if (settings.quality === 'high') {
      videoBitsPerSecond = 30000000;
    } else if (settings.quality === 'lossless') {
      videoBitsPerSecond = 80000000;
    }
    if (settings.type === 'mp4') {
      mimeType = 'video/mp4;codecs=h264';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/mp4';
      }
    } else if (settings.type === 'avi') {
      mimeType = 'video/avi';
    } else if (settings.type === 'gif') {
      setAnimationExportStatus('GIF export is not supported in this browser. Use WebM or MP4.');
      return;
    } else {
      if (settings.quality === 'lossless') {
        mimeType = 'video/webm;codecs=vp9';
      } else {
        mimeType = 'video/webm;codecs=vp9';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/webm;codecs=vp8';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/webm';
      }
    }
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      setAnimationExportStatus('Selected file type is not supported in this browser.');
      return;
    }

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = exportWidth;
    exportCanvas.height = exportHeight;
    exportRenderer = new THREE.WebGLRenderer({ canvas: exportCanvas, antialias: true, preserveDrawingBuffer: false });
    exportRenderer.setSize(exportWidth, exportHeight, false);
    exportRenderer.setPixelRatio(1);
    exportRenderer.outputColorSpace = renderer.outputColorSpace;
    exportRenderer.toneMapping = renderer.toneMapping;
    exportRenderer.toneMappingExposure = renderer.toneMappingExposure;

    const stream = exportCanvas.captureStream(effectiveFps);
    const chunks = [];
    let writable = null;
    let writeChain = Promise.resolve();
    if (window.showSaveFilePicker) {
      const pickerTypes = [
        {
          description: 'Video',
          accept: {
            'video/webm': ['.webm'],
            'video/mp4': ['.mp4'],
            'video/avi': ['.avi'],
          },
        },
      ];
      const handle = await window.showSaveFilePicker({
        suggestedName: settings.fileName,
        types: pickerTypes,
      });
      writable = await handle.createWritable();
    }

    const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond });
    recorder.ondataavailable = (event) => {
      if (!event.data || event.data.size === 0) return;
      if (writable) {
        writeChain = writeChain.then(() => writable.write(event.data));
      } else {
        chunks.push(event.data);
      }
    };

    const stopPromise = new Promise((resolve) => {
      recorder.onstop = () => resolve();
    });

    recorder.start(250);

    const totalFrames = Math.max(1, Math.ceil((durationMs / 1000) * effectiveFps) + 1);
    const track = stream.getVideoTracks()[0];
    for (let i = 0; i < totalFrames; i += 1) {
      const timeMs = Math.min(durationMs, (i / effectiveFps) * 1000);
      keyframeSystem.applyAtTime(timeMs);
      cameraSystem.setCameraHelperVisible(false);
      exportRenderer.render(scene, cameraSystem.getCamera());
      if (track && typeof track.requestFrame === 'function') {
        track.requestFrame();
      }
      if (i % Math.max(1, Math.floor(effectiveFps)) === 0) {
        const pct = Math.round((i / totalFrames) * 100);
        setAnimationExportStatus(`Recording animation... ${pct}%`);
      }
      await new Promise((resolve) => setTimeout(resolve, 1000 / effectiveFps));
    }

    recorder.stop();
    await stopPromise;
    await writeChain;

    if (writable) {
      await writable.close();
      closeAnimationExportDialog();
    } else {
      const blob = new Blob(chunks, { type: mimeType });
      if (!blob.size) {
        setAnimationExportStatus('Export failed to render.');
        return;
      }
      setAnimationExportStatus('Saving...');
      await saveBlobAsFile(blob, settings.fileName);
      closeAnimationExportDialog();
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Export failed.';
    setAnimationExportStatus(message);
  } finally {
    keyframeSystem.stopPlayback();
    if (prevCameraState) {
      cameraSystem.applyExternalCameraState(prevCameraState);
    }
    if (prevLightState && lightSystem) {
      lightSystem.applyLightState(prevLightState);
    }
    if (prevModelSelection && modelSelector) {
      modelSelector.applySelectionSnapshot(prevModelSelection, { persist: false });
    }
    cameraSystem.setCameraHelperVisible(prevCameraHelperVisible);
    renderer.setPixelRatio(prevPixelRatio);
    renderer.setSize(prevSize.x, prevSize.y, false);
    cameraSystem.handleResize();
    if (controls && typeof controls.handleResize === 'function') {
      controls.handleResize();
    }
    if (exportRenderer) {
      exportRenderer.dispose();
    }
    uiElements.forEach((el) => el.classList.remove('ui-hidden'));
    animationExportSaveBtn.disabled = false;
    animationExportClose.disabled = false;
  }
}


async function resetGeneralSettings() {
  localStorage.removeItem(AUTO_RELOAD_STORAGE_KEY);
  localStorage.removeItem(AUTO_RELOAD_INTERVAL_KEY);
  localStorage.removeItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY);
  localStorage.removeItem(MODEL_DEFAULT_VERSION_KEY);
  const defaultType = 'orbit';
  if (defaultControlTypeSelect) {
    defaultControlTypeSelect.value = defaultType;
  }
  cameraSystem.setDefaultControlType(defaultType);
  localStorage.setItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY, defaultType);
  applyControlsType(defaultType, false);
  setAutoReloadIntervalMs(1000);
  if (autoReloadIntervalInput) {
    autoReloadIntervalInput.value = '1000';
  }
  autoReloadEnabled = true;
  setAutoReload(true);
  await fetch('/set_preview_dir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: '' }),
  }).catch(() => null);
  await initModels();
  settingsSystem?.refreshPreviewInfo();
}

function openPreviewSettingsDialog(listData) {
  if (!previewSettingsDialog || !previewSettingsFileSelect) return;
  pendingSettingsList = listData;
  previewSettingsFileSelect.innerHTML = '';
  if (Array.isArray(listData.files)) {
    listData.files.forEach((file) => {
      const option = document.createElement('option');
      option.value = file.path;
      option.textContent = `Model Settings (${file.name})`;
      option.dataset.source = 'model';
      previewSettingsFileSelect.appendChild(option);
    });
  }

  previewSettingsCustomOrder.forEach((key) => {
    const entry = previewSettingsCustomFiles.get(key);
    if (!entry) return;
    const option = document.createElement('option');
    option.value = key;
    option.textContent = entry.label;
    option.dataset.source = 'custom';
    previewSettingsFileSelect.appendChild(option);
  });

  const chooseOption = document.createElement('option');
  chooseOption.value = '__choose__';
  chooseOption.textContent = 'Choose file…';
  chooseOption.dataset.source = 'choose';
  previewSettingsFileSelect.appendChild(chooseOption);

  if (previewSettingsFileSelect.options.length > 0) {
    previewSettingsFileSelect.value = previewSettingsFileSelect.options[0].value;
  }
  if (previewSettingsGeneral) previewSettingsGeneral.checked = true;
  if (previewSettingsTheme) previewSettingsTheme.checked = true;
  if (previewSettingsCamera) previewSettingsCamera.checked = true;
  if (previewSettingsLighting) previewSettingsLighting.checked = true;
  if (previewSettingsAnimation) previewSettingsAnimation.checked = true;
  previewSettingsDialog.classList.add('is-open');
}

function closePreviewSettingsDialog() {
  if (!previewSettingsDialog) return;
  previewSettingsDialog.classList.remove('is-open');
  pendingSettingsList = null;
  previewSettingsCustomFiles.clear();
  previewSettingsCustomOrder.length = 0;
  if (previewSettingsFileSelect) {
    previewSettingsFileSelect.innerHTML = '';
  }
}

async function fetchPreviewSettingsList() {
  const resp = await fetch('/preview_settings_list.json').catch(() => null);
  if (!resp || !resp.ok) return null;
  const data = await resp.json().catch(() => null);
  if (!data || !Array.isArray(data.files) || data.files.length === 0) return null;
  return data;
}

async function checkPreviewSettingsPrompt() {
  const listData = await fetchPreviewSettingsList();
  if (!listData) return;

  const file = listData.files?.[0];
  if (!file?.path) return;
  const resp = await fetch(`/preview_settings_file?path=${encodeURIComponent(file.path)}`).catch(() => null);
  if (!resp || !resp.ok) return;
  const payload = await resp.json().catch(() => null);
  if (!payload) return;

  applySettingsPayload(payload, {
    general: false,
    theme: false,
    camera: true,
    lighting: true,
    animation: true,
  });
}

function resetCameraSettings() {
  localStorage.removeItem('pymfcad_cameras_v1');
  cameraSystem.initCameraStates();
  cameraSystem.resetCameraHome();
  syncCameraControlSelect();
}

function resetLightingSettings() {
  localStorage.removeItem(LIGHTS_STORAGE_KEY);
  lightSystem.resetLights();
}

function resetThemeSettings() {
  themeManager.resetAllThemes();
  if (themeSelect) {
    themeSelect.value = 'dark';
  }
  syncThemeInputs('dark');
}

function buildModelKey(entry) {
  const type = (entry?.type || 'unknown').toLowerCase();
  const id = entry?.id || entry?.name || 'unknown';
  return `${type}|${id}`;
}

function buildModelSelectionPayload() {
  if (!modelSelector || !modelManager) return null;
  const snapshot = modelSelector.getSelectionSnapshot();
  const entries = modelManager.getModelList() || [];
  const byKey = {};
  entries.forEach((entry, idx) => {
    const key = buildModelKey(entry);
    const visible = snapshot.models?.[`glb_cb_${idx}`];
    const version = snapshot.versions?.[`glb_ver_${idx}`] || entry.versionId;
    if (visible === undefined && version === undefined) return;
    byKey[key] = {
      visible: visible !== undefined ? !!visible : true,
      version,
      name: entry?.name,
      type: entry?.type,
    };
  });
  const groups = {};
  Object.entries(snapshot.groups || {}).forEach(([id, checked]) => {
    groups[id] = !!checked;
  });
  return { byKey, groups };
}

function sortVersionIds(ids) {
  return ids.sort((a, b) => {
    if (a === 'v0') return -1;
    if (b === 'v0') return 1;
    const aMatch = /^v(\d+)$/i.exec(a);
    const bMatch = /^v(\d+)$/i.exec(b);
    const aNum = aMatch ? Number.parseInt(aMatch[1], 10) : Number.POSITIVE_INFINITY;
    const bNum = bMatch ? Number.parseInt(bMatch[1], 10) : Number.POSITIVE_INFINITY;
    if (aNum !== bNum) return aNum - bNum;
    return a.localeCompare(b);
  });
}

function getGlobalVersionId(strategy = 'smallest') {
  const entries = modelManager?.getModelList?.() || [];
  const union = new Set();
  entries.forEach((entry) => {
    (entry?.versions || []).forEach((ver) => union.add(ver.id));
  });
  const ids = Array.from(union);
  if (!ids.length) return null;
  const sorted = sortVersionIds(ids);
  return strategy === 'largest' ? sorted[sorted.length - 1] : sorted[0];
}

function applyDefaultVersionVisibilityConstraint() {
  if (!modelSelector?.applyVersionConstraint || !modelManager) return;
  if (getDefaultModelVersionStrategy() !== 'smallest') return;
  const target = getGlobalVersionId('smallest');
  if (!target) return;
  modelSelector.applyVersionConstraint(target, { persist: false });
  if (modelManager?.setModelVersionSelections) {
    modelManager.setModelVersionSelections(modelSelector.getSelectionSnapshot().versions, { force: true });
  }
  modelManager.updateVisibility();
}

function buildCameraPayload() {
  const raw = localStorage.getItem('pymfcad_cameras_v1');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

function buildSettingsPayload() {
  const payload = {
    version: 2,
    general: {
      autoReloadEnabled,
      autoReloadIntervalMs,
      axesVisible: axes?.visible ?? true,
      defaultControlsType: cameraSystem.getDefaultControlType?.() || defaultControlTypeSelect?.value || 'orbit',
      defaultModelVersion: getDefaultModelVersionStrategy(),
      measurementUnits: measurementUnits,
    },
    camera: buildCameraPayload(),
    lights: lightSystem.getLightState(),
    models: buildModelSelectionPayload(),
    theme: themeManager.getThemeState(),
    animation: {
      keyframes: keyframeSystem ? keyframeSystem.getKeyframes() : [],
      exportDefaults: {
        resolution: animationExportResolutionSelect?.value || '1920x1080',
        fps: Number.parseInt(animationExportFpsInput?.value || '30', 10) || 30,
        quality: animationExportQualitySelect?.value || 'medium',
        type: animationExportTypeSelect?.value || 'webm',
      },
    },
  };
  return payload;
}

async function saveSettingsToFile() {
  const payload = buildSettingsPayload();
  const jsonText = JSON.stringify(payload, null, 2);
  try {
    if (window.showSaveFilePicker) {
      const handle = await window.showSaveFilePicker({
        suggestedName: 'pymfcad-settings.json',
        types: [
          {
            description: 'JSON',
            accept: { 'application/json': ['.json'] },
          },
        ],
      });
      const writable = await handle.createWritable();
      await writable.write(jsonText);
      await writable.close();
      showToast('Settings exported.');
      return;
    }
    const blob = new Blob([jsonText], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'pymfcad-settings.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showToast('Settings exported.');
  } catch (error) {
    if (error && error.name === 'AbortError') return;
    showToast('Export failed.', { variant: 'error' });
  }
}

async function saveSettingsToPreviewDir() {
  if (!menuSaveBtn) return;
  const previewInfo = await fetch('/preview_info.json').then((resp) => resp.json()).catch(() => null);
  if (!previewInfo || previewInfo.source === 'demo' || previewInfo.source === 'none') {
    menuSaveBtn.disabled = true;
    showToast('Save unavailable for demo device.', { variant: 'error' });
    return;
  }

  const payload = buildSettingsPayload();
  const resp = await fetch('/save_preview_settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => null);
  if (resp && resp.ok) {
    showToast('Settings saved to preview folder.');
  } else {
    showToast('Save failed.', { variant: 'error' });
  }
}

async function updateMenuSaveAvailability() {
  if (!menuSaveBtn) return;
  const previewInfo = await fetch('/preview_info.json').then((resp) => resp.json()).catch(() => null);
  const disabled = !previewInfo || previewInfo.source === 'demo' || previewInfo.source === 'none';
  menuSaveBtn.disabled = disabled;
}

async function refreshPreviewDirList() {
  if (!previewDirBaseInput || !previewDirSelect) return;
  const basePath = previewDirBaseInput.value.trim();
  if (!basePath) return;
  const resp = await fetch(`/preview_dir_list?path=${encodeURIComponent(basePath)}`).catch(() => null);
  if (!resp || !resp.ok) {
    showToast('Unable to list folders.', { variant: 'error' });
    return;
  }
  const data = await resp.json().catch(() => null);
  previewDirSelect.innerHTML = '';
  const folders = Array.isArray(data?.folders) ? data.folders : [];
  if (!folders.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No valid folders found';
    previewDirSelect.appendChild(opt);
    return;
  }
  folders.forEach((entry) => {
    const opt = document.createElement('option');
    opt.value = entry.path;
    opt.textContent = entry.name;
    previewDirSelect.appendChild(opt);
  });
  previewDirSelect.value = folders[0].path;
}

async function openPreviewDirDialog() {
  if (!previewDirDialog) return;
  const info = await fetch('/preview_info.json').then((resp) => resp.json()).catch(() => null);
  const cwd = info?.cwd || '';
  if (previewDirBaseInput) {
    previewDirBaseInput.value = cwd;
  }
  await refreshPreviewDirList();
  previewDirDialog.classList.add('is-open');
}

function closePreviewDirDialog() {
  if (!previewDirDialog) return;
  previewDirDialog.classList.remove('is-open');
}

function applySettingsPayload(payload, sections = {}) {
  if (!payload || typeof payload !== 'object') return;
  const apply = {
    general: sections.general !== false,
    theme: sections.theme !== false,
    camera: sections.camera !== false,
    lighting: sections.lighting !== false,
    animation: sections.animation !== false,
  };

  const isNewFormat = payload.version >= 2 || payload.general || payload.camera || payload.models;

  if (apply.general && isNewFormat) {
    const general = payload.general || {};
    if (general.axesVisible !== undefined) {
      applyAxesState(!!general.axesVisible);
    }
    if (general.defaultControlsType) {
      cameraSystem.setDefaultControlType(general.defaultControlsType);
      if (defaultControlTypeSelect) defaultControlTypeSelect.value = general.defaultControlsType;
    }
    if (Number.isFinite(general.autoReloadIntervalMs)) {
      setAutoReloadIntervalMs(general.autoReloadIntervalMs);
      if (autoReloadIntervalInput) autoReloadIntervalInput.value = String(general.autoReloadIntervalMs);
    }
    if (general.autoReloadEnabled !== undefined) {
      autoReloadEnabled = !!general.autoReloadEnabled;
      setAutoReload(autoReloadEnabled);
    }
    if (general.defaultModelVersion) {
      if (defaultModelVersionSelect) {
        defaultModelVersionSelect.value = general.defaultModelVersion;
      }
      setDefaultModelVersionStrategy(general.defaultModelVersion);
      modelManager.applyDefaultVersionStrategy();
      if (modelSelector) {
        const snapshot = modelSelector.getSelectionSnapshot();
        modelSelector.applySelectionSnapshot({
          ...snapshot,
          versions: modelManager.getVersionSelections(),
        }, { persist: true });
      }
      applyDefaultVersionVisibilityConstraint();
      modelManager.loadAllModels().then(() => {
        cameraSystem.setTargetToModelCenter({ persist: false });
        lightSystem.updateDirectionalLightTargets();
      });
    }
    if (general.measurementUnits) {
      setMeasurementUnits(general.measurementUnits);
    }
  }

  if (apply.camera && isNewFormat && payload.camera) {
    localStorage.setItem('pymfcad_cameras_v1', JSON.stringify(payload.camera));
    cameraSystem.initCameraStates();
    cameraSystem.resetCameraHome();
    syncCameraControlSelect();
  }

  if (apply.general && isNewFormat && payload.models && modelSelector) {
    const entries = modelManager.getModelList() || [];
    const snapshot = modelSelector.getSelectionSnapshot();
    const nextModels = { ...(snapshot.models || {}) };
    const nextGroups = { ...(snapshot.groups || {}) };
    const nextVersions = { ...(snapshot.versions || {}) };

    if (payload.models.groups) {
      Object.entries(payload.models.groups).forEach(([id, checked]) => {
        nextGroups[id] = !!checked;
      });
    }

    if (payload.models.byKey) {
      entries.forEach((entry, idx) => {
        const key = buildModelKey(entry);
        const item = payload.models.byKey[key];
        if (!item) return;
        nextModels[`glb_cb_${idx}`] = item.visible !== undefined ? !!item.visible : true;
        if (item.version) {
          nextVersions[`glb_ver_${idx}`] = item.version;
        }
      });
    }

    modelSelector.applySelectionSnapshot({
      models: nextModels,
      groups: nextGroups,
      versions: nextVersions,
    }, { persist: true });
    if (modelManager?.setModelVersionSelections) {
      modelManager.setModelVersionSelections(nextVersions, { force: true });
    }
    modelManager.updateVisibility();
  }


  if (!isNewFormat) return;

  if (apply.theme && payload.theme) {
    themeManager.setThemeState(payload.theme);
    if (themeSelect) {
      themeSelect.value = payload.theme.activeTheme || themeSelect.value;
      syncThemeInputs(themeSelect.value);
    }
  }

  if (apply.lighting && payload.lights) {
    lightSystem.applyLightState(payload.lights);
  }

  if (apply.animation && payload.animation) {
    applyAnimationSettingsPayload(payload.animation);
  }
}

async function loadSettingsFromFile(file) {
  const text = await file.text();
  const parsed = JSON.parse(text);
  applySettingsPayload(parsed);
}

function syncCameraControlSelect() {
  if (!cameraControlTypeSelect) return;
  const isHome = cameraSystem.isHomeMode();
  const activeState = cameraSystem.getActiveCameraState();
  if (isHome || !activeState) {
    cameraControlTypeSelect.disabled = false;
    const currentType = typeof cameraSystem.getCurrentControlType === 'function'
      ? cameraSystem.getCurrentControlType()
      : cameraSystem.getDefaultControlType();
    cameraControlTypeSelect.value = currentType || cameraSystem.getDefaultControlType();
    return;
  }
  cameraControlTypeSelect.disabled = false;
  cameraControlTypeSelect.value = activeState.controlType || cameraSystem.getDefaultControlType();
}

cameraSystem.bindCameraUI({
  cameraList: cameraListEl,
  cameraStrip: cameraStripEl,
  cameraModeButton: cameraModeBtn,
  resetButton: resetCameraBtn,
  homeButton: homeCameraBtn,
  centerTargetButton: centerTargetBtn,
  updateButton: updateCameraBtn,
  addButtons: [addCameraBtn, addCameraBtnSettings],
  removeButton: removeCameraBtnSettings,
  presetButtons: cameraPresetButtons,
  inputFields: {
    yaw: camYaw,
    pitch: camPitch,
    targetX: camTargetX,
    targetY: camTargetY,
    targetZ: camTargetZ,
    distance: camDistance,
    roll: camRoll,
    fov: camFov,
  },
});

keyframeSystem.bindUI({
  panel: animationPanel,
  toggleButton: animationToggleBtn,
  panelBody: animationPanelBody,
  list: keyframeListEl,
  empty: keyframeEmptyEl,
  addButton: addKeyframeBtn,
  moveUpButton: moveKeyframeUpBtn,
  moveDownButton: moveKeyframeDownBtn,
  removeButton: removeKeyframeBtn,
  playButton: keyframePlayBtn,
  playFromStartButton: keyframePlayFromStartBtn,
  transitionMenu,
  transitionMenuList,
  modelSelectorContainer: modelSelectorEl,
  modelSelectorHost: keyframeModelSelectorHost,
  settingsDialog,
  settingsDialogClose,
  lightSystem,
  modelManager,
  cameraList: cameraListEl,
  addCameraBtnSettings: addCameraBtnSettings,
  removeCameraBtnSettings: removeCameraBtnSettings,
});

lightSystem.bindLightUI({
  dialog: settingsDialog,
  openBtn: settingsDialogBtn,
  closeBtn: settingsDialogClose,
  cameraList: cameraListEl,
  cameraStrip: cameraStripEl,
  ambientColor: ambientColorInput,
  ambientIntensity: ambientIntensityInput,
  directionalList: directionalLightsList,
  addDirLight: addDirLightBtn,
  removeDirLight: removeDirLightBtn,
  onOpen: () => {
    if (settingsSystem) {
      settingsSystem.activateTab('general');
    }
  },
});

// Preview viewer is bound per tab via settingsSystem.

function initAxesToggle() {
  if (!axesToggleBtn) return;
  const savedAxes = localStorage.getItem(AXES_STORAGE_KEY);
  axes.visible = savedAxes !== 'false';
  axesToggleBtn.textContent = axes.visible ? 'Axes: On' : 'Axes: Off';
  axesToggleBtn.addEventListener('click', () => {
    axes.visible = !axes.visible;
    localStorage.setItem(AXES_STORAGE_KEY, String(axes.visible));
    axesToggleBtn.textContent = axes.visible ? 'Axes: On' : 'Axes: Off';
    scheduleHistoryCapture();
  });
}

let autoReloadEnabled = localStorage.getItem(AUTO_RELOAD_STORAGE_KEY) !== 'false';
let autoReloadInterval = null;
let autoReloadOffline = false;
let autoReloadIntervalMs = Number.parseInt(
  localStorage.getItem(AUTO_RELOAD_INTERVAL_KEY) || '1000',
  10
);
if (!Number.isFinite(autoReloadIntervalMs) || autoReloadIntervalMs < 250) {
  autoReloadIntervalMs = 1000;
}

let viewCubeSystem = null;

function createViewCubeSystem({ container, cameraSystem }) {
  if (!container) return null;
  const cubeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  cubeRenderer.setPixelRatio(window.devicePixelRatio || 1);
  cubeRenderer.setClearColor(0x000000, 0);
  container.appendChild(cubeRenderer.domElement);

  const cubeScene = new THREE.Scene();
  const cubeCamera = new THREE.PerspectiveCamera(35, 1, 0.1, 10);
  cubeCamera.position.set(0, 0, 3);
  cubeCamera.up.set(0, 1, 0);

  const getCssVar = (name, fallback) => {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  };

  const getThemeColors = () => ({
    face: getCssVar('--panel', '#ffffff'),
    text: getCssVar('--text', '#111111'),
    edge: getCssVar('--button-border', '#333333'),
    hover: getCssVar('--button-bg-active', '#888888'),
  });

  let themeCache = null;
  const makeLabelTexture = (label, colors) => {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = colors.face;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = colors.edge;
    ctx.lineWidth = 6;
    ctx.strokeRect(3, 3, canvas.width - 6, canvas.height - 6);
    ctx.fillStyle = colors.text;
    ctx.font = 'bold 44px Inter, system-ui, -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, canvas.width / 2, canvas.height / 2);
    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    texture.anisotropy = cubeRenderer.capabilities.getMaxAnisotropy();
    return texture;
  };

  const faceLabels = ['RIGHT', 'LEFT', 'TOP', 'BOTTOM', 'FRONT', 'BACK'];
  const faceMaterials = faceLabels.map((label) =>
    new THREE.MeshBasicMaterial({ map: makeLabelTexture(label, getThemeColors()) })
  );

  const cube = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), faceMaterials);
  cubeScene.add(cube);

  const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x111111 });
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(cube.geometry), edgeMaterial);
  cube.add(edges);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const hotspots = [];

  const hotspotMaterial = new THREE.MeshBasicMaterial({
    color: 0x000000,
    opacity: 0,
    transparent: true,
    depthWrite: false,
  });

  const hoverIndicator = new THREE.Mesh(
    new THREE.SphereGeometry(0.16, 20, 20),
    new THREE.MeshBasicMaterial({ color: 0x888888, transparent: true, opacity: 0.6 })
  );
  hoverIndicator.visible = false;
  cube.add(hoverIndicator);

  const addHotspot = (direction, radius) => {
    const dir = direction.clone().normalize();
    const maxComponent = Math.max(Math.abs(dir.x), Math.abs(dir.y), Math.abs(dir.z));
    const t = maxComponent > 0 ? 0.5 / maxComponent : 0.5;
    const position = dir.clone().multiplyScalar(t);
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 16, 16), hotspotMaterial);
    mesh.position.copy(position);
    mesh.userData.direction = dir;
    cube.add(mesh);
    hotspots.push(mesh);
  };

  const axis = [-1, 0, 1];
  axis.forEach((x) => {
    axis.forEach((y) => {
      axis.forEach((z) => {
        if (x === 0 && y === 0 && z === 0) return;
        const sum = Math.abs(x) + Math.abs(y) + Math.abs(z);
        if (sum === 1) {
          addHotspot(new THREE.Vector3(x, y, z), 0.23);
        } else if (sum === 2) {
          addHotspot(new THREE.Vector3(x, y, z), 0.21);
        } else {
          addHotspot(new THREE.Vector3(x, y, z), 0.2);
        }
      });
    });
  });

  const getTargetObject = () => {
    const bboxScene = modelManager.getBoundingBoxScene();
    if (bboxScene && bboxScene.visible) return bboxScene;
    return modelManager.buildVisibleGroup();
  };

  const getCameraPoseForDirection = (direction) => {
    const targetObj = getTargetObject();
    if (!targetObj) return null;
    const box = new THREE.Box3().setFromObject(targetObj);
    if (!Number.isFinite(box.min.x) || !Number.isFinite(box.max.x)) return null;

    const center = box.getCenter(new THREE.Vector3());
    const corners = [
      new THREE.Vector3(box.min.x, box.min.y, box.min.z),
      new THREE.Vector3(box.min.x, box.min.y, box.max.z),
      new THREE.Vector3(box.min.x, box.max.y, box.min.z),
      new THREE.Vector3(box.min.x, box.max.y, box.max.z),
      new THREE.Vector3(box.max.x, box.min.y, box.min.z),
      new THREE.Vector3(box.max.x, box.min.y, box.max.z),
      new THREE.Vector3(box.max.x, box.max.y, box.min.z),
      new THREE.Vector3(box.max.x, box.max.y, box.max.z),
    ];

    const dir = direction.clone().normalize();
    const upRef = new THREE.Vector3(0, 1, 0);
    if (Math.abs(dir.dot(upRef)) > 0.98) {
      upRef.set(0, 0, 1);
    }
    const right = new THREE.Vector3().crossVectors(upRef, dir).normalize();
    const up = new THREE.Vector3().crossVectors(dir, right).normalize();

    const size = renderer.getSize(new THREE.Vector2());
    const aspect = size.x / Math.max(1, size.y);
    const vFov = THREE.MathUtils.degToRad(perspectiveCamera.fov);
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
    const tanH = Math.tan(hFov / 2);
    const tanV = Math.tan(vFov / 2);

    let maxDistance = 0.1;
    corners.forEach((corner) => {
      const local = corner.clone().sub(center);
      const zOffset = local.dot(dir);
      const x = local.dot(right);
      const y = local.dot(up);
      const needH = zOffset + Math.abs(x) / Math.max(1e-6, tanH);
      const needV = zOffset + Math.abs(y) / Math.max(1e-6, tanV);
      maxDistance = Math.max(maxDistance, needH, needV);
    });

    const padding = 1.15;
    const distance = Math.max(0.1, maxDistance * padding);
    const position = center.clone().add(dir.multiplyScalar(distance));
    return { position, target: center };
  };

  const applyCameraDirection = (direction) => {
    const pose = getCameraPoseForDirection(direction);
    if (!pose) return;
    cameraSystem.setCameraPose(pose.position, pose.target, 0);
    cameraSystem.syncCameraInputs();
    cameraSystem.updateCameraModeButton();
  };

  const handlePointer = (event) => {
    const rect = container.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    pointer.x = x * 2 - 1;
    pointer.y = -(y * 2 - 1);
    raycaster.setFromCamera(pointer, cubeCamera);
    const hits = raycaster.intersectObjects(hotspots, true);
    if (hits.length === 0) {
      hoverIndicator.visible = false;
      container.style.cursor = 'default';
      return;
    }
    const hit = hits[0].object;
    hoverIndicator.visible = true;
    hoverIndicator.position.copy(hit.position);
    container.style.cursor = 'pointer';
    if (event.type === 'pointerdown') {
      const dir = hit.userData?.direction;
      if (dir) {
        applyCameraDirection(dir);
      }
    }
  };

  container.addEventListener('pointerdown', handlePointer);
  container.addEventListener('pointermove', handlePointer);
  container.addEventListener('pointerleave', () => {
    hoverIndicator.visible = false;
    container.style.cursor = 'default';
  });

  function handleResize() {
    const rect = container.getBoundingClientRect();
    const size = Math.max(1, Math.floor(Math.min(rect.width, rect.height)));
    cubeRenderer.setSize(size, size, false);
    cubeCamera.aspect = 1;
    cubeCamera.updateProjectionMatrix();
  }

  function updateTheme() {
    const colors = getThemeColors();
    const key = `${colors.face}|${colors.text}|${colors.edge}|${colors.hover}`;
    if (key === themeCache) return;
    themeCache = key;
    faceMaterials.forEach((mat, idx) => {
      if (mat.map) mat.map.dispose();
      mat.map = makeLabelTexture(faceLabels[idx], colors);
      mat.needsUpdate = true;
    });
    edgeMaterial.color.set(colors.edge);
    hoverIndicator.material.color.set(colors.hover);
  }

  function render() {
    updateTheme();
    const mainCamera = cameraSystem.getCamera();
    const camQuat = new THREE.Quaternion();
    mainCamera.getWorldQuaternion(camQuat);
    cube.quaternion.copy(camQuat).invert();
    cubeRenderer.render(cubeScene, cubeCamera);
  }

  handleResize();
  return { render, handleResize };
}

function setAutoReloadStatus(state) {
  if (!reloadModelBtn) return;
  if (state === 'offline') {
    reloadModelBtn.textContent = 'Auto Reload: OFFLINE';
    reloadModelBtn.classList.remove('is-active');
    reloadModelBtn.classList.add('is-warning');
  } else {
    reloadModelBtn.classList.toggle('is-warning', false);
    reloadModelBtn.textContent = autoReloadEnabled ? 'Auto Reload: ON' : 'Auto Reload: OFF';
    reloadModelBtn.classList.toggle('is-active', autoReloadEnabled);
  }
}

async function handleModelRefresh() {
  const result = await modelManager.checkForUpdates();
  if (result.error === 'offline') {
    autoReloadOffline = true;
    setAutoReloadStatus('offline');
    return;
  }

  if (autoReloadOffline) {
    autoReloadOffline = false;
    setAutoReloadStatus('ok');
  }
  if (result.listChanged) {
    modelManager.setModelList(result.list);
    modelManager.setDefaultVersionStrategy(getDefaultModelVersionStrategy());
    modelManager.applyDefaultVersionStrategy();
    modelSelector.build({
      files: modelManager.getModelList(),
      signature: result.signature,
      resetSelection: true,
    });
    if (modelSelector) {
      const snapshot = modelSelector.getSelectionSnapshot();
      modelSelector.applySelectionSnapshot({
        ...snapshot,
        versions: modelManager.getVersionSelections(),
      }, { persist: false });
    }
    applyDefaultVersionVisibilityConstraint();
    modelManager.setModelVersionSelections(modelSelector.getSelectionSnapshot().versions);
    modelManager.updateVisibility();
    await modelManager.loadAllModels();
    cameraSystem.setTargetToModelCenter({ persist: false });
    lightSystem.ensureDefaultLight();
    lightSystem.updateDirectionalLightTargets();
    settingsSystem?.refreshPreviewInfo();
    await updateMenuSaveAvailability();
    await checkPreviewSettingsPrompt();
    return;
  }

  if (result.filesChanged) {
    if (Array.isArray(result.changedEntries) && result.changedEntries.length > 0) {
      await modelManager.reloadModels(result.changedEntries);
    } else {
      await modelManager.loadAllModels();
    }
    lightSystem.ensureDefaultLight();
    lightSystem.updateDirectionalLightTargets();
    settingsSystem?.refreshPreviewInfo();
    await updateMenuSaveAvailability();
  }
}

function setAutoReloadIntervalMs(nextIntervalMs) {
  autoReloadIntervalMs = nextIntervalMs;
  localStorage.setItem(AUTO_RELOAD_INTERVAL_KEY, String(autoReloadIntervalMs));
  if (autoReloadEnabled) {
    setAutoReload(true);
  }
}

async function resetAllSettings() {
  skipBeforeUnloadSave = true;
  suppressLocalPersistence = true;
  localStorage.removeItem(AUTO_RELOAD_STORAGE_KEY);
  localStorage.removeItem(AUTO_RELOAD_INTERVAL_KEY);
  localStorage.removeItem(AXES_STORAGE_KEY);
  localStorage.removeItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY);
  localStorage.removeItem('pymfcad_theme');
  localStorage.removeItem('pymfcad_theme_defs_v1');
  localStorage.removeItem('pymfcad_cameras_v1');
  localStorage.removeItem('pymfcad_keyframes_v1');
  localStorage.removeItem('pymfcad_model_selector_collapsed');
  localStorage.removeItem('pymfcad_model_selection_v2');
  localStorage.removeItem('pymfcad_model_selection_v3');
  localStorage.removeItem('pymfcad_controls_type');
  localStorage.removeItem(LIGHTS_STORAGE_KEY);
  await fetch('/set_preview_dir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: '' }),
  }).catch(() => null);
  window.location.reload();
}

function setAutoReload(enabled) {
  autoReloadEnabled = enabled;
  localStorage.setItem(AUTO_RELOAD_STORAGE_KEY, String(enabled));
  if (!autoReloadOffline) {
    setAutoReloadStatus('ok');
  }
  if (enabled) {
    if (autoReloadInterval) {
      clearInterval(autoReloadInterval);
      autoReloadInterval = null;
    }
    autoReloadInterval = setInterval(handleModelRefresh, autoReloadIntervalMs);
  } else if (autoReloadInterval) {
    clearInterval(autoReloadInterval);
    autoReloadInterval = null;
  }
}

async function initModels() {
  const list = await modelManager.fetchModelList();
  if (!list) {
    autoReloadOffline = true;
    setAutoReloadStatus('offline');
    return;
  }
  modelManager.setModelList(list);
  modelManager.setDefaultVersionStrategy(getDefaultModelVersionStrategy());
  modelManager.applyDefaultVersionStrategy();
  modelSelector.build({ files: modelManager.getModelList(), signature: modelManager.getListSignature() });
  if (modelSelector) {
    const snapshot = modelSelector.getSelectionSnapshot();
    modelSelector.applySelectionSnapshot({
      ...snapshot,
      versions: modelManager.getVersionSelections(),
    }, { persist: false });
  }
  applyDefaultVersionVisibilityConstraint();
  modelManager.setModelVersionSelections(modelSelector.getSelectionSnapshot().versions);
  await modelManager.loadAllModels();
  clearMeasurement();
  cameraSystem.setTargetToModelCenter({ persist: false });
  lightSystem.ensureDefaultLight();
  lightSystem.updateDirectionalLightTargets();
  settingsSystem?.refreshPreviewInfo();
  await updateMenuSaveAvailability();
  await checkPreviewSettingsPrompt();
}

function initAutoReload() {
  if (reloadModelBtn) {
    reloadModelBtn.addEventListener('click', () => {
      setAutoReload(!autoReloadEnabled);
    });
  }
  setAutoReload(autoReloadEnabled);
}

function initResizing() {
  window.addEventListener('resize', () => {
    cameraSystem.handleResize();
    renderer.setSize(window.innerWidth, window.innerHeight);
    if (controls && typeof controls.handleResize === 'function') {
      controls.handleResize();
    }
    previewSystem.updateSize();
    viewCubeSystem?.handleResize();
  });
}

function initHistoryObservers() {
  const handleControlChange = () => scheduleHistoryCapture();
  const handleControlEnd = () => pushHistorySnapshot();
  [orbitControls, trackballControls].forEach((ctrl) => {
    if (!ctrl || typeof ctrl.addEventListener !== 'function') return;
    ctrl.addEventListener('change', handleControlChange);
    ctrl.addEventListener('end', handleControlEnd);
  });

  [resetCameraBtn, homeCameraBtn, centerTargetBtn, updateCameraBtn, cameraModeBtn,
    addCameraBtn, addCameraBtnSettings, removeCameraBtnSettings].forEach((btn) => {
    if (!btn) return;
    btn.addEventListener('click', () => scheduleHistoryCapture());
  });

  cameraPresetButtons.forEach((btn) => {
    btn.addEventListener('click', () => scheduleHistoryCapture());
  });

  if (autoReloadIntervalInput) {
    autoReloadIntervalInput.addEventListener('change', () => scheduleHistoryCapture());
  }

  if (themeSelect) {
    themeSelect.addEventListener('change', () => scheduleHistoryCapture());
  }

  if (themeResetBtn) {
    themeResetBtn.addEventListener('click', () => scheduleHistoryCapture());
  }

  if (themeToCustomBtn) {
    themeToCustomBtn.addEventListener('click', () => scheduleHistoryCapture());
  }

  Object.values(themeInputs || {}).forEach((input) => {
    if (!input) return;
    input.addEventListener('input', () => scheduleHistoryCapture());
  });

  if (keyframeListEl) {
    keyframeListEl.addEventListener('input', () => scheduleHistoryCapture());
    keyframeListEl.addEventListener('change', () => scheduleHistoryCapture());
  }

  if (keyframeSystem) {
    const wrap = (name) => {
      const original = keyframeSystem[name];
      if (typeof original !== 'function') return;
      keyframeSystem[name] = (...args) => {
        const result = original(...args);
        if (!historyState.isApplying) scheduleHistoryCapture();
        return result;
      };
    };
    ['addKeyframe', 'removeActiveKeyframe', 'setKeyframes', 'resetKeyframes', 'applyCameraModeToKeyframes', 'clearSelection'].forEach(wrap);
  }
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  cameraSystem.updateCameraIcon();
  renderer.clear();
  renderer.render(scene, cameraSystem.getCamera());
  if (measurementScene.visible) {
    renderer.clearDepth();
    renderer.render(measurementScene, cameraSystem.getCamera());
  }
  viewCubeSystem?.render();
  previewSystem.render();
}

function isEditableTarget(target) {
  if (!target) return false;
  if (target.isContentEditable) return true;
  const tagName = target.tagName;
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT';
}

function isEditingInput() {
  return isEditableTarget(document.activeElement);
}

function isAnyDialogOpen() {
  return !!document.querySelector('.modal.is-open');
}

async function init() {
  document.body.classList.add('is-loading');
  viewCubeSystem = createViewCubeSystem({ container: viewCubeEl, cameraSystem });
  themeManager = createThemeManager({ scene, axes });
  themeManager.initTheme();
  themeManager.bindThemeUI({
    themeSelect,
    themeInputs,
    resetBtn: themeResetBtn,
    saveCustomBtn: themeToCustomBtn,
  });
  initAxesToggle();
  if (docsBtn) {
    docsBtn.addEventListener('click', () => {
      window.open('/docs/', '_blank', 'noopener');
    });
  }

  if (menuOpenBtn) {
    menuOpenBtn.addEventListener('click', async () => {
      await openPreviewDirDialog();
    });
  }

  if (menuSaveSettingsBtn) {
    menuSaveSettingsBtn.addEventListener('click', async () => {
      await saveSettingsToFile();
    });
  }

  if (menuLoadSettingsBtn) {
    menuLoadSettingsBtn.addEventListener('click', async () => {
      try {
        const listData = await fetchPreviewSettingsList();
        if (listData) {
          openPreviewSettingsDialog(listData);
          return;
        }
        openPreviewSettingsDialog({ files: [] });
      } catch (error) {
        openPreviewSettingsDialog({ files: [] });
      }
    });
  }

  if (menuSettingsBtn) {
    menuSettingsBtn.addEventListener('click', async () => {
      settingsDialogBtn?.click();
    });
  }

  if (menuSaveBtn) {
    menuSaveBtn.addEventListener('click', async () => {
      await saveSettingsToPreviewDir();
    });
  }
  if (menuUndoBtn) {
    menuUndoBtn.addEventListener('click', () => {
      undoHistory();
    });
  }
  if (menuRedoBtn) {
    menuRedoBtn.addEventListener('click', () => {
      redoHistory();
    });
  }
  if (saveSnapshotBtn) {
    saveSnapshotBtn.addEventListener('click', () => {
      openSnapshotDialog();
    });
  }

  if (animationExportBtn) {
    animationExportBtn.addEventListener('click', () => {
      openAnimationExportDialog();
    });
  }


  if (animationExportQualitySelect) {
    animationExportQualitySelect.addEventListener('change', () => {
      syncAnimationExportTypeForQuality();
    });
  }

  if (snapshotDialogClose) {
    snapshotDialogClose.addEventListener('click', () => {
      closeSnapshotDialog();
    });
  }

  if (animationExportClose) {
    animationExportClose.addEventListener('click', () => {
      closeAnimationExportDialog();
    });
  }

  if (snapshotSaveBtn) {
    snapshotSaveBtn.addEventListener('click', async () => {
      await handleSnapshotSave();
    });
  }

  if (animationExportSaveBtn) {
    animationExportSaveBtn.addEventListener('click', async () => {
      await handleAnimationExport();
    });
  }

  if (resetSettingsApplyBtn && resetSettingsSelect) {
    resetSettingsApplyBtn.addEventListener('click', async () => {
      const value = resetSettingsSelect.value;
      if (value === 'general') {
        await resetGeneralSettings();
      } else if (value === 'theme') {
        resetThemeSettings();
      } else if (value === 'camera') {
        resetCameraSettings();
      } else if (value === 'lighting') {
        resetLightingSettings();
      } else if (value === 'animation') {
        if (keyframeSystem) keyframeSystem.resetKeyframes();
      } else if (value === 'all') {
        await resetAllSettings();
      }
    });
  }

  if (settingsFileInput) {
    settingsFileInput.addEventListener('change', async () => {
      const file = settingsFileInput.files?.[0];
      if (!file) return;
      await loadSettingsFromFile(file);
    });
  }

  if (previewSettingsClose) {
    previewSettingsClose.addEventListener('click', () => {
      closePreviewSettingsDialog();
    });
  }


  if (previewSettingsLoadBtn) {
    previewSettingsLoadBtn.addEventListener('click', async () => {
      if (!pendingSettingsList || !previewSettingsFileSelect) return;
      const path = previewSettingsFileSelect.value;
      if (!path) return;
      if (path === '__choose__') {
        previewSettingsFileInput?.click();
        return;
      }
      if (previewSettingsCustomFiles.has(path)) {
        const entry = previewSettingsCustomFiles.get(path);
        if (entry?.payload) {
          applySettingsPayload(entry.payload, {
            general: previewSettingsGeneral?.checked !== false,
            theme: previewSettingsTheme?.checked !== false,
            camera: previewSettingsCamera?.checked !== false,
            lighting: previewSettingsLighting?.checked !== false,
            animation: previewSettingsAnimation?.checked !== false,
          });
        }
        return;
      }
      const resp = await fetch(`/preview_settings_file?path=${encodeURIComponent(path)}`);
      if (!resp.ok) {
        closePreviewSettingsDialog();
        return;
      }
      const payload = await resp.json().catch(() => null);
      if (payload) {
        applySettingsPayload(payload, {
          general: previewSettingsGeneral?.checked !== false,
          theme: previewSettingsTheme?.checked !== false,
          camera: previewSettingsCamera?.checked !== false,
          lighting: previewSettingsLighting?.checked !== false,
          animation: previewSettingsAnimation?.checked !== false,
        });
      }
    });
  }

  if (previewSettingsFileInput) {
    previewSettingsFileInput.addEventListener('change', async () => {
      const file = previewSettingsFileInput.files?.[0];
      if (!file) return;
      const text = await file.text();
      const parsed = JSON.parse(text);
      const key = `local:${Date.now()}:${file.name}`;
      const label = file.webkitRelativePath && file.webkitRelativePath.length > 0
        ? file.webkitRelativePath
        : file.name;
      previewSettingsCustomFiles.set(key, {
        label: `Local (${label})`,
        payload: parsed,
      });
      previewSettingsCustomOrder.push(key);
      if (pendingSettingsList) {
        openPreviewSettingsDialog(pendingSettingsList);
        previewSettingsFileSelect.value = key;
      }
    });
  }

  if (previewSettingsFileSelect && previewSettingsFileInput) {
    previewSettingsFileSelect.addEventListener('change', () => {
      if (previewSettingsFileSelect.value === '__choose__') {
        previewSettingsFileInput.value = '';
        previewSettingsFileInput.click();
      }
    });
  }

  if (previewSettingsDialog) {
    previewSettingsDialog.addEventListener('click', (event) => {
      if (event.target === previewSettingsDialog) {
        closePreviewSettingsDialog();
      }
    });
  }

  if (previewDirClose) {
    previewDirClose.addEventListener('click', () => {
      closePreviewDirDialog();
    });
  }

  if (previewDirCancelBtn) {
    previewDirCancelBtn.addEventListener('click', () => {
      closePreviewDirDialog();
    });
  }

  if (previewDirRefreshBtn) {
    previewDirRefreshBtn.addEventListener('click', async () => {
      await refreshPreviewDirList();
    });
  }

  if (previewDirOpenBtn) {
    previewDirOpenBtn.addEventListener('click', async () => {
      if (!previewDirSelect || !previewDirSelect.value) return;
      const resp = await fetch('/set_preview_dir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: previewDirSelect.value }),
      }).catch(() => null);
      if (!resp || !resp.ok) {
        const data = await resp?.json().catch(() => null);
        showToast(data?.error || 'Unable to set preview folder.', { variant: 'error' });
        return;
      }
      closePreviewDirDialog();
      await initModels();
      await updateMenuSaveAvailability();
      scheduleHistoryCapture();
    });
  }

  if (animationExportDialog) {
    animationExportDialog.addEventListener('click', (event) => {
      if (event.target === animationExportDialog) {
        closeAnimationExportDialog();
      }
    });
  }

  window.addEventListener('keydown', (event) => {
    if (!event) return;
    if (isEditableTarget(event.target) || isEditingInput()) return;
    if (isAnyDialogOpen()) return;
    if (event.key === 'Escape' && measurementState.enabled) {
      event.preventDefault();
      setMeasurementEnabled(false);
      return;
    }
    const isCtrl = event.ctrlKey || event.metaKey;
    if (!isCtrl) return;
    const key = event.key?.toLowerCase();
    if (key === 'o') {
      event.preventDefault();
      menuOpenBtn?.click();
    } else if (key === 's') {
      event.preventDefault();
      if (menuSaveBtn?.disabled) {
        showToast('Save unavailable for demo device.', { variant: 'error' });
        return;
      }
      menuSaveBtn?.click();
    } else if (key === 'z') {
      event.preventDefault();
      undoHistory();
    } else if (key === 'y') {
      event.preventDefault();
      redoHistory();
    }
  });

  window.addEventListener('keydown', (event) => {
    if (!event) return;
    if (!isAnyDialogOpen()) return;
    const isEditing = isEditableTarget(event.target) || isEditingInput();
    event.stopImmediatePropagation();
    if (!isEditing) {
      event.preventDefault();
    }
  }, true);

  window.addEventListener('keyup', (event) => {
    if (!event) return;
    if (!isAnyDialogOpen()) return;
    const isEditing = isEditableTarget(event.target) || isEditingInput();
    event.stopImmediatePropagation();
    if (!isEditing) {
      event.preventDefault();
    }
  }, true);

  syncAnimationExportTypeForQuality();

  if (measurementToggleBtn) {
    measurementToggleBtn.addEventListener('click', () => {
      setMeasurementEnabled(!measurementState.enabled);
    });
  }

  if (measurementClearBtn) {
    measurementClearBtn.addEventListener('click', () => {
      clearMeasurement();
    });
  }

  if (measurementPanelToggleBtn) {
    measurementPanelToggleBtn.addEventListener('click', () => {
      const nextVisible = measurementPanel ? measurementPanel.classList.contains('is-hidden') : false;
      setMeasurementPanelVisible(nextVisible);
    });
  }

  setMeasurementEnabled(false);
  setMeasurementPanelVisible(false);
  clearMeasurement({ keepPrompt: true });

  if (defaultControlTypeSelect) {
    const savedType = localStorage.getItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY) || 'orbit';
    defaultControlTypeSelect.value = savedType;
    cameraSystem.setDefaultControlType(savedType);
    applyControlsType(savedType, false);
    defaultControlTypeSelect.addEventListener('change', () => {
      const nextType = defaultControlTypeSelect.value;
      cameraSystem.setDefaultControlType(nextType);
      localStorage.setItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY, nextType);
      if (cameraSystem.isHomeMode() || !cameraSystem.getActiveCameraState()) {
        applyControlsType(nextType, false);
      }
      scheduleHistoryCapture();
    });
  }

  if (cameraControlTypeSelect) {
    syncCameraControlSelect();
    cameraControlTypeSelect.addEventListener('change', () => {
      const nextType = cameraControlTypeSelect.value;
      if (cameraSystem.isHomeMode() || !cameraSystem.getActiveCameraState()) {
        cameraSystem.setDefaultControlType(nextType);
        localStorage.setItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY, nextType);
        applyControlsType(nextType, false);
        syncCameraControlSelect();
        return;
      }
      cameraSystem.setActiveCameraControlType(nextType);
      applyControlsType(nextType, false);
      syncCameraControlSelect();
    });
  }
  settingsSystem = createSettingsSystem({
    settingsDialog,
    previewSystem,
    previewViewers: {
      camera: lightDialogViewer,
      lights: lightsDialogViewer,
      'keyframe-models': keyframeModelsViewer,
    },
    cwdValueInput,
    modelSourceValueInput,
    previewDirInput,
    previewDirSetBtn,
    previewDirResetBtn,
    previewDirWarningEl,
    autoReloadIntervalInput,
    getAutoReloadIntervalMs: () => autoReloadIntervalMs,
    setAutoReloadIntervalMs,
    initModels,
  });
  if (previewSystem?.setInteractionDependencies) {
    previewSystem.setInteractionDependencies({
      lightSystem,
      getActiveTab: settingsSystem.getActiveTab,
      buildVisibleGroup: modelManager.buildVisibleGroup,
      world,
    });
  }
  keyframeSystem.setEditorDependencies({
    settingsDialog,
    settingsDialogClose,
    settingsSystem,
    lightSystem,
    modelSelector,
    modelManager,
    cameraList: cameraListEl,
    addCameraBtnSettings: addCameraBtnSettings,
    removeCameraBtnSettings: removeCameraBtnSettings,
  });
  settingsSystem.initTabs('general');
  settingsSystem.initGeneralSettings();
  if (defaultModelVersionSelect) {
    defaultModelVersionSelect.value = getDefaultModelVersionStrategy();
    defaultModelVersionSelect.addEventListener('change', async () => {
      setDefaultModelVersionStrategy(defaultModelVersionSelect.value);
      modelManager.applyDefaultVersionStrategy();
      if (modelSelector) {
        const snapshot = modelSelector.getSelectionSnapshot();
        modelSelector.applySelectionSnapshot({
          ...snapshot,
          versions: modelManager.getVersionSelections(),
        }, { persist: true });
      }
      await modelManager.loadAllModels();
      lightSystem.updateDirectionalLightTargets();
      scheduleHistoryCapture();
    });
  }
  suppressLocalPersistence = true;
  await initModels();
  await updateMenuSaveAvailability();

  cameraSystem.initCameraStates();
  cameraSystem.resetCameraHome();
  restorePersistedViewState();
  suppressLocalPersistence = false;
  syncCameraControlSelect();

  window.addEventListener('beforeunload', () => {
    if (skipBeforeUnloadSave || suppressLocalPersistence) return;
    saveLightState();
  });

  initAutoReload();
  initHistoryObservers();
  initResizing();
  document.body.classList.remove('is-loading');
  animate();
  pushHistorySnapshot();
}

init();
