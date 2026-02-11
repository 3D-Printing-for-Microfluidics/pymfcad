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

const AUTO_RELOAD_STORAGE_KEY = 'openmfd_auto_reload';
const AUTO_RELOAD_INTERVAL_KEY = 'openmfd_auto_reload_interval_ms';
const AXES_STORAGE_KEY = 'openmfd_axes_visible';
const DEFAULT_CONTROLS_TYPE_STORAGE_KEY = 'openmfd_default_controls_type';
const MODEL_SETTINGS_BEHAVIOR_KEY = 'openmfd_model_settings_behavior';
const MODEL_DEFAULT_VERSION_KEY = 'openmfd_model_default_version';
const LIGHTS_STORAGE_KEY = 'openmfd_lights_v1';

const sceneState = createScene();
const {
  scene,
  world,
  axes,
  renderer,
  controls: initialControls,
  perspectiveCamera,
  orthographicCamera,
  setControlsType,
  THREE,
} = sceneState;
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
renderer.domElement.addEventListener('dblclick', (event) => {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  const camera = cameraSystem.getCamera();
  raycaster.setFromCamera(pointer, camera);
  const targetGroup = modelManager.buildVisibleGroup();
  if (!targetGroup) return;
  targetGroup.matrixAutoUpdate = false;
  targetGroup.matrix.copy(world.matrixWorld);
  targetGroup.updateMatrixWorld(true);
  const hits = raycaster.intersectObject(targetGroup, true);
  const hit = hits.find((entry) => entry.object?.isMesh);
  if (!hit) return;

  const roll = cameraSystem.getCameraState().roll || 0;
  cameraSystem.setCameraPose(camera.position.clone(), hit.point.clone(), roll);
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
const modelSettingsBehaviorSelect = document.getElementById('modelSettingsBehaviorSelect');
const defaultModelVersionSelect = document.getElementById('defaultModelVersionSelect');
const resetSettingsSelect = document.getElementById('resetSettingsSelect');
const resetSettingsApplyBtn = document.getElementById('resetSettingsApplyBtn');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const loadSettingsBtn = document.getElementById('loadSettingsBtn');
const settingsFileInput = document.getElementById('settingsFileInput');
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
const snapshotDialog = document.getElementById('snapshotDialog');
const snapshotDialogClose = document.getElementById('snapshotDialogClose');
const snapshotSaveBtn = document.getElementById('snapshotSaveBtn');
const snapshotResolutionSelect = document.getElementById('snapshotResolution');
const snapshotProgress = document.getElementById('snapshotProgress');
const snapshotPathTracingProgress = document.getElementById('snapshotPathTracingProgress');
const snapshotPathTracingLabel = document.getElementById('snapshotPathTracingLabel');
const snapshotPathTracingFill = document.getElementById('snapshotPathTracingFill');
const snapshotRendererSelect = document.getElementById('snapshotRenderer');
const snapshotPathTracingOptions = document.getElementById('snapshotPathTracingOptions');
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
const animationPathTracingProgress = document.getElementById('animationPathTracingProgress');
const animationPathTracingLabel = document.getElementById('animationPathTracingLabel');
const animationPathTracingFill = document.getElementById('animationPathTracingFill');
const pathTracingFrame = document.getElementById('pathTracingFrame');
let pathTracingFrameReady = false;
const animationRendererSelect = document.getElementById('animationRenderer');
const animationPathTracingOptions = document.getElementById('animationPathTracingOptions');
const animationPtPixelRatio = document.getElementById('animationPtPixelRatio');
const animationPtExposure = document.getElementById('animationPtExposure');
const animationPtSamples = document.getElementById('animationPtSamples');

function resetPathTracingFrame() {
  if (!pathTracingFrame) return;
  pathTracingFrameReady = false;
  updatePathTracingProgress(0, 1);
  const currentSrc = pathTracingFrame.getAttribute('src') || pathTracingFrame.src;
  if (!currentSrc) return;
  pathTracingFrame.src = currentSrc;
}

let settingsSystem = null;
let themeManager = null;
let pendingSettingsList = null;
const previewSettingsCustomFiles = new Map();
const previewSettingsCustomOrder = [];
let suppressLocalPersistence = false;
let skipBeforeUnloadSave = false;

if (pathTracingFrame) {
  pathTracingFrame.style.display = 'block';
  pathTracingFrame.style.position = 'fixed';
  pathTracingFrame.style.left = '-10000px';
  pathTracingFrame.style.top = '0';
  pathTracingFrame.style.width = '64px';
  pathTracingFrame.style.height = '64px';
  pathTracingFrame.style.opacity = '0';
  pathTracingFrame.style.pointerEvents = 'none';
  pathTracingFrame.style.border = '0';
}

window.addEventListener('message', (event) => {
  if (event.origin !== window.location.origin) return;
  const payload = event.data || {};
  if (payload.type === 'openmfd-pathtracing-ready') {
    pathTracingFrameReady = true;
  }
  if (payload.type === 'openmfd-pathtracing-progress') {
    updatePathTracingProgress(payload.current, payload.total);
  }
});

function updatePathTracingProgress(current, total) {
  const safeTotal = Math.max(1, Number.isFinite(total) ? total : 1);
  const safeCurrent = Math.max(0, Number.isFinite(current) ? current : 0);
  const pct = Math.min(100, Math.round((safeCurrent / safeTotal) * 100));
  if (snapshotPathTracingLabel) {
    snapshotPathTracingLabel.textContent = `${safeCurrent} / ${safeTotal}`;
  }
  if (snapshotPathTracingFill) {
    snapshotPathTracingFill.style.width = `${pct}%`;
  }
  if (animationPathTracingLabel) {
    animationPathTracingLabel.textContent = `${safeCurrent} / ${safeTotal}`;
  }
  if (animationPathTracingFill) {
    animationPathTracingFill.style.width = `${pct}%`;
  }
}

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

function getModelSettingsBehavior() {
  return localStorage.getItem(MODEL_SETTINGS_BEHAVIOR_KEY) || 'dialog';
}

function setModelSettingsBehavior(value) {
  const next = value || 'dialog';
  localStorage.setItem(MODEL_SETTINGS_BEHAVIOR_KEY, next);
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
  return 'openmfd-viewport.png';
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
    pathTracing: {
      pixelRatio: Math.min(1, Number.parseFloat(snapshotPtPixelRatio?.value || '0.8') || 0.8),
      exposure: Number.parseFloat(snapshotPtExposure?.value || '1.5') || 1.5,
      samples: Math.min(1024, Number.parseInt(snapshotPtSamples?.value || '64', 10) || 64),
    },
  };
}

function normalizeAnimationName(name, type) {
  const trimmed = (name || '').trim() || 'openmfd-animation';
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
    pathTracing: {
      pixelRatio: Math.min(1, Number.parseFloat(animationPtPixelRatio?.value || '0.8') || 0.8),
      exposure: Number.parseFloat(animationPtExposure?.value || '1.5') || 1.5,
      samples: Math.min(1024, Number.parseInt(animationPtSamples?.value || '32', 10) || 32),
    },
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

function updatePathTracingOptionVisibility() {
  const snapshotMode = snapshotRendererSelect?.value || 'raster';
  if (snapshotPathTracingOptions) {
    snapshotPathTracingOptions.style.display = snapshotMode === 'pathtracing' ? '' : 'none';
  }
  if (snapshotPathTracingProgress) {
    snapshotPathTracingProgress.style.display = snapshotMode === 'pathtracing' ? '' : 'none';
  }
  const animationMode = animationRendererSelect?.value || 'raster';
  if (animationPathTracingOptions) {
    animationPathTracingOptions.style.display = animationMode === 'pathtracing' ? '' : 'none';
  }
  if (animationPathTracingProgress) {
    animationPathTracingProgress.style.display = animationMode === 'pathtracing' ? '' : 'none';
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
  updatePathTracingOptionVisibility();
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
  updatePathTracingOptionVisibility();
  setAnimationExportStatus('');
  animationExportDialog.classList.add('is-open');
}

function closeAnimationExportDialog() {
  if (!animationExportDialog) return;
  animationExportDialog.classList.remove('is-open');
  setAnimationExportStatus('');
}

function getPathTracingModelPaths() {
  const entries = modelManager.getModelList();
  if (!entries || !entries.length) return [];
  const snapshot = modelSelector.getSelectionSnapshot();
  const paths = [];
  entries.forEach((entry, idx) => {
    if ((entry?.type || '').toLowerCase() === 'bounding box') return;
    if (!modelSelector.getModelVisibility(idx)) return;
    const versionKey = `glb_ver_${idx}`;
    const versionId = snapshot?.versions?.[versionKey] || entry.versionId;
    const version = (entry.versions || []).find((ver) => ver.id === versionId) || entry.versions?.[0];
    if (!version?.file) return;
    try {
      const url = new URL(version.file, window.location.href).href;
      paths.push(url);
    } catch (e) {
      paths.push(version.file);
    }
  });
  return Array.from(new Set(paths));
}

function getPathTracingCameraState() {
  if (!cameraSystem?.getCameraState) return null;
  const state = cameraSystem.getCameraState();
  if (!state) return null;
  return {
    pos: state.pos,
    target: state.target,
    roll: state.roll,
    fov: state.fov,
    mode: state.mode,
  };
}

function getPathTracingLightState() {
  if (!lightSystem?.getLightState) return null;
  const state = lightSystem.getLightState();
  const modelCenter = modelManager.getModelCenterModel();
  if (!state || !modelCenter) return null;

  const ambientColor = new THREE.Color(state.ambient?.color || '#000000').convertSRGBToLinear();
  const directional = (state.directional || []).map((light) => {
    const pos = light.position && Number.isFinite(light.position.x)
      ? new THREE.Vector3(light.position.x, light.position.y, light.position.z)
      : modelCenter.clone().add(new THREE.Vector3(10, 10, 10));
    const target = light.targetPosition && Number.isFinite(light.targetPosition.x)
      ? new THREE.Vector3(light.targetPosition.x, light.targetPosition.y, light.targetPosition.z)
      : modelCenter.clone();
    const color = new THREE.Color(light.color || '#ffffff').convertSRGBToLinear();
    return {
      type: light.type || 'directional',
      position: { x: pos.x, y: pos.y, z: pos.z },
      target: { x: target.x, y: target.y, z: target.z },
      color: [color.r, color.g, color.b],
      intensity: Number.isFinite(light.intensity) ? light.intensity : 1,
      distance: Number.isFinite(light.distance) ? light.distance : 0,
      angle: Number.isFinite(light.angle) ? light.angle : undefined,
      decay: Number.isFinite(light.decay) ? light.decay : 1,
    };
  });

  return {
    ambient: {
      color: [ambientColor.r, ambientColor.g, ambientColor.b],
      intensity: Number.isFinite(state.ambient?.intensity) ? state.ambient.intensity : 0,
    },
    directional,
  };
}

function postPathTracingModels(paths) {
  if (!pathTracingFrame || !pathTracingFrame.contentWindow) return;
  pathTracingFrame.contentWindow.postMessage({
    type: 'openmfd-pathtracing-models',
    modelPaths: paths,
  }, window.location.origin);
}

function postPathTracingCamera() {
  if (!pathTracingFrame || !pathTracingFrame.contentWindow) return;
  const cameraState = getPathTracingCameraState();
  if (!cameraState) return;
  pathTracingFrame.contentWindow.postMessage({
    type: 'openmfd-pathtracing-camera',
    camera: cameraState,
  }, window.location.origin);
}

function postPathTracingLights() {
  if (!pathTracingFrame || !pathTracingFrame.contentWindow) return;
  const lightsState = getPathTracingLightState();
  if (!lightsState) return;
  pathTracingFrame.contentWindow.postMessage({
    type: 'openmfd-pathtracing-lights',
    lights: lightsState,
  }, window.location.origin);
}

function sendPathTracingState() {
  const paths = getPathTracingModelPaths();
  if (!paths.length) return false;
  postPathTracingModels(paths);
  postPathTracingCamera();
  postPathTracingLights();
  return true;
}

async function ensurePathTracingReady() {
  if (!pathTracingFrame) {
    throw new Error('Path tracing renderer is unavailable.');
  }
  if (pathTracingFrameReady && pathTracingFrame.contentWindow?.openmfdPathTracing?.requestRender) {
    return;
  }

  await new Promise((resolve) => {
    const onLoad = () => {
      pathTracingFrameReady = true;
      pathTracingFrame.removeEventListener('load', onLoad);
      resolve();
    };
    const readyState = pathTracingFrame.contentDocument?.readyState;
    if (readyState === 'complete' && pathTracingFrame.contentWindow) {
      pathTracingFrameReady = true;
      resolve();
      return;
    }
    pathTracingFrame.addEventListener('load', onLoad);
    if (!pathTracingFrame.contentWindow) {
      pathTracingFrame.src = pathTracingFrame.src;
    }
  });

  await new Promise((resolve) => {
    const start = performance.now();
    const tick = () => {
      const apiReady = pathTracingFrame.contentWindow?.openmfdPathTracing?.requestRender;
      if (apiReady) {
        resolve();
        return;
      }
      if (performance.now() - start > 10000) {
        resolve();
        return;
      }
      requestAnimationFrame(tick);
    };
    tick();
  });
}

async function renderPathTracingSnapshot({ width, height, pixelRatio, exposure, samples }) {
  await ensurePathTracingReady();
  if (!sendPathTracingState()) {
    throw new Error('No visible models selected for path tracing.');
  }
  const requestRender = pathTracingFrame.contentWindow?.openmfdPathTracing?.requestRender;
  if (!requestRender) throw new Error('Path tracing renderer is not ready.');
  return requestRender({
    width,
    height,
    pixelRatio,
    exposure,
    samples,
  });
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
  if (settings.renderer === 'pathtracing' && settings.pathTracing?.samples > 300) {
    setSnapshotStatus('High sample count may cause GPU reset. If it fails, lower samples or resolution.');
  } else {
    setSnapshotStatus(settings.renderer === 'pathtracing' ? 'Rendering path traced snapshot...' : 'Rendering snapshot...');
  }
  cameraSystem.setCameraHelperVisible(false);

  try {
    let blob = null;
    const renderWidth = exportWidth;
    const renderHeight = exportHeight;
    let saveHandle = null;
    if (settings.renderer === 'pathtracing') {
      if (window.showSaveFilePicker) {
        saveHandle = await window.showSaveFilePicker({
          suggestedName: settings.fileName,
          types: [
            {
              description: 'PNG Image',
              accept: { 'image/png': ['.png'] },
            },
          ],
        });
      }
      blob = await renderPathTracingSnapshot({
        width: renderWidth,
        height: renderHeight,
        pixelRatio: settings.pathTracing?.pixelRatio ?? 0.8,
        exposure: settings.pathTracing?.exposure ?? 1.5,
        samples: settings.pathTracing?.samples ?? 64,
      });
      resetPathTracingFrame();
    } else {
      blob = await renderRasterSnapshot({ width: renderWidth, height: renderHeight });
    }

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
    if (settings.renderer === 'pathtracing') {
      resetPathTracingFrame();
    }
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
  return frames.reduce((total, frame) => {
    const hold = Number.isFinite(frame?.holdDuration) ? Math.max(0, frame.holdDuration) : 0;
    const transition = Number.isFinite(frame?.transitionDuration) ? Math.max(0, frame.transitionDuration) : 0;
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
  const usePathTracing = settings.renderer === 'pathtracing';
  if (!usePathTracing && (!renderer?.domElement?.captureStream || typeof MediaRecorder === 'undefined')) {
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
  setAnimationExportStatus(usePathTracing ? 'Rendering path traced frames...' : 'Recording animation...');

  try {
    renderer.setPixelRatio(1);
    applyExportCameraSize(exportWidth, exportHeight);

    if (usePathTracing) {
      const suggestedName = settings.fileName || `openmfd-animation.${settings.type || 'webm'}`;
      const saveHandle = window.showSaveFilePicker
        ? await window.showSaveFilePicker({
          suggestedName,
          types: [
            {
              description: 'Video',
              accept: {
                'video/webm': ['.webm'],
                'video/mp4': ['.mp4'],
                'video/avi': ['.avi'],
              },
            },
          ],
        })
        : null;

      const totalFrames = Math.max(1, Math.ceil((durationMs / 1000) * effectiveFps) + 1);

      const startResp = await fetch('/pathtracing_animation/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!startResp.ok) {
        setAnimationExportStatus('Failed to start path tracing export.');
        return;
      }
      const startData = await startResp.json();
      const sessionId = startData.session_id;
      if (!sessionId) {
        setAnimationExportStatus('Path tracing export session failed.');
        return;
      }

      for (let i = 0; i < totalFrames; i += 1) {
        const timeMs = Math.min(durationMs, (i / effectiveFps) * 1000);
        keyframeSystem.applyAtTime(timeMs);
        cameraSystem.setCameraHelperVisible(false);

        const blob = await renderPathTracingSnapshot({
          width: exportWidth,
          height: exportHeight,
          pixelRatio: settings.pathTracing?.pixelRatio ?? 0.8,
          exposure: settings.pathTracing?.exposure ?? 1.5,
          samples: settings.pathTracing?.samples ?? 32,
        });

        if (!blob) {
          setAnimationExportStatus('Path tracing frame failed to render.');
          return;
        }

        const form = new FormData();
        form.append('session_id', sessionId);
        form.append('index', String(i));
        form.append('frame', blob, `frame_${String(i).padStart(4, '0')}.png`);

        const uploadResp = await fetch('/pathtracing_animation/frame', {
          method: 'POST',
          body: form,
        });
        if (!uploadResp.ok) {
          setAnimationExportStatus('Failed to upload path tracing frame.');
          return;
        }

        if (i % Math.max(1, Math.floor(effectiveFps)) === 0) {
          const pct = Math.round((i / totalFrames) * 100);
          setAnimationExportStatus(`Rendering path traced frames... ${pct}%`);
        }
      }

      const finishResp = await fetch('/pathtracing_animation/finish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          fps: effectiveFps,
          type: settings.type,
          quality: settings.quality,
          filename: settings.fileName,
        }),
      });
      if (!finishResp.ok) {
        setAnimationExportStatus('Failed to encode path traced animation.');
        return;
      }
      const videoBlob = await finishResp.blob();
      if (!videoBlob.size) {
        setAnimationExportStatus('Path traced animation failed to render.');
        return;
      }
      resetPathTracingFrame();
      setAnimationExportStatus('Saving...');
      if (saveHandle) {
        const writable = await saveHandle.createWritable();
        await writable.write(videoBlob);
        await writable.close();
      } else {
        await saveBlobAsFile(videoBlob, settings.fileName);
      }
      closeAnimationExportDialog();
      return;
    }

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
  localStorage.removeItem(MODEL_SETTINGS_BEHAVIOR_KEY);
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
  if (modelSettingsBehaviorSelect) {
    modelSettingsBehaviorSelect.value = 'dialog';
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
  const behavior = getModelSettingsBehavior();
  if (behavior === 'dialog') {
    openPreviewSettingsDialog(listData || { files: [] });
    return;
  }
  if (!listData) return;
  if (behavior === 'ignore') return;

  const file = listData.files?.[0];
  if (!file?.path) return;
  const resp = await fetch(`/preview_settings_file?path=${encodeURIComponent(file.path)}`).catch(() => null);
  if (!resp || !resp.ok) return;
  const payload = await resp.json().catch(() => null);
  if (!payload) return;

  if (behavior === 'camera-lights-animation') {
    applySettingsPayload(payload, {
      general: false,
      theme: false,
      camera: true,
      lighting: true,
      animation: true,
    });
    return;
  }
  if (behavior === 'all') {
    applySettingsPayload(payload, {
      general: true,
      theme: true,
      camera: true,
      lighting: true,
      animation: true,
    });
  }
}

function resetCameraSettings() {
  localStorage.removeItem('openmfd_cameras_v1');
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
  const raw = localStorage.getItem('openmfd_cameras_v1');
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
      modelSettingsBehavior: getModelSettingsBehavior(),
      defaultModelVersion: getDefaultModelVersionStrategy(),
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
  if (window.showSaveFilePicker) {
    const handle = await window.showSaveFilePicker({
      suggestedName: 'openmfd-settings.json',
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
    return;
  }
  const blob = new Blob([jsonText], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'openmfd-settings.json';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
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
    if (general.modelSettingsBehavior) {
      if (modelSettingsBehaviorSelect) {
        modelSettingsBehaviorSelect.value = general.modelSettingsBehavior;
      }
      setModelSettingsBehavior(general.modelSettingsBehavior);
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
  }

  if (apply.camera && isNewFormat && payload.camera) {
    localStorage.setItem('openmfd_cameras_v1', JSON.stringify(payload.camera));
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
  localStorage.removeItem(MODEL_SETTINGS_BEHAVIOR_KEY);
  localStorage.removeItem('openmfd_theme');
  localStorage.removeItem('openmfd_theme_defs_v1');
  localStorage.removeItem('openmfd_cameras_v1');
  localStorage.removeItem('openmfd_keyframes_v1');
  localStorage.removeItem('openmfd_model_selector_collapsed');
  localStorage.removeItem('openmfd_model_selection_v2');
  localStorage.removeItem('openmfd_model_selection_v3');
  localStorage.removeItem('openmfd_controls_type');
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
  cameraSystem.setTargetToModelCenter({ persist: false });
  lightSystem.ensureDefaultLight();
  lightSystem.updateDirectionalLightTargets();
  settingsSystem?.refreshPreviewInfo();
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

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  cameraSystem.updateCameraIcon();
  renderer.render(scene, cameraSystem.getCamera());
  viewCubeSystem?.render();
  previewSystem.render();
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

  if (snapshotRendererSelect) {
    snapshotRendererSelect.addEventListener('change', updatePathTracingOptionVisibility);
  }
  if (animationRendererSelect) {
    animationRendererSelect.addEventListener('change', updatePathTracingOptionVisibility);
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

  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', async () => {
      await saveSettingsToFile();
    });
  }

  if (loadSettingsBtn) {
    loadSettingsBtn.addEventListener('click', async () => {
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

  if (animationExportDialog) {
    animationExportDialog.addEventListener('click', (event) => {
      if (event.target === animationExportDialog) {
        closeAnimationExportDialog();
      }
    });
  }

  syncAnimationExportTypeForQuality();
  updatePathTracingOptionVisibility();

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
  if (modelSettingsBehaviorSelect) {
    modelSettingsBehaviorSelect.value = getModelSettingsBehavior();
    modelSettingsBehaviorSelect.addEventListener('change', () => {
      setModelSettingsBehavior(modelSettingsBehaviorSelect.value);
    });
  }
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
    });
  }
  suppressLocalPersistence = true;
  await initModels();

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
  initResizing();
  document.body.classList.remove('is-loading');
  animate();
}

init();
