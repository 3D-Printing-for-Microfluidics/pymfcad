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

keyframeSystem = createKeyframeSystem({ cameraSystem, modelManager });

const previewSystem = createPreviewSystem({ scene, controls, cameraSystem });

lightSystem = createLightSystem({
  scene,
  world,
  cameraSystem,
  previewSystem,
  getModelCenterModel: modelManager.getModelCenterModel,
});

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
const camPosX = document.getElementById('camPosX');
const camPosY = document.getElementById('camPosY');
const camPosZ = document.getElementById('camPosZ');
const camTargetX = document.getElementById('camTargetX');
const camTargetY = document.getElementById('camTargetY');
const camTargetZ = document.getElementById('camTargetZ');
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
const snapshotFileNameInput = document.getElementById('snapshotFileName');
const snapshotProgress = document.getElementById('snapshotProgress');
const animationExportDialog = document.getElementById('animationExportDialog');
const animationExportClose = document.getElementById('animationExportClose');
const animationExportResolutionSelect = document.getElementById('animationExportResolution');
const animationExportFpsInput = document.getElementById('animationExportFps');
const animationExportQualitySelect = document.getElementById('animationExportQuality');
const animationExportTypeSelect = document.getElementById('animationExportType');
const animationExportFileNameInput = document.getElementById('animationExportFileName');
const animationExportSaveBtn = document.getElementById('animationExportSaveBtn');
const animationExportProgress = document.getElementById('animationExportProgress');

let settingsSystem = null;
let themeManager = null;
let pendingSettingsList = null;
const previewSettingsCustomFiles = new Map();
const previewSettingsCustomOrder = [];

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
  const trimmed = (name || '').trim();
  if (!trimmed) return 'openmfd-viewport.png';
  return trimmed.toLowerCase().endsWith('.png') ? trimmed : `${trimmed}.png`;
}

function getSnapshotSettings() {
  const fileName = normalizeSnapshotName(snapshotFileNameInput?.value);
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
  const fileName = normalizeAnimationName(animationExportFileNameInput?.value, type);
  const resolutionValue = animationExportResolutionSelect?.value || '';
  const [w, h] = resolutionValue.split('x').map((value) => Number.parseInt(value, 10));
  const width = Number.isFinite(w) && w > 0 ? w : window.innerWidth;
  const height = Number.isFinite(h) && h > 0 ? h : window.innerHeight;
  return { width, height, fps, quality, type, fileName };
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
    blob = await renderRasterSnapshot({ width: renderWidth, height: renderHeight });

    if (!blob) {
      setSnapshotStatus('Snapshot failed to render.');
      return;
    }
    setSnapshotStatus('Saving...');
    await saveBlobAsFile(blob, settings.fileName);
    closeSnapshotDialog();
  } catch (err) {
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
  lightSystem.resetLights();
}

function resetThemeSettings() {
  themeManager.resetAllThemes();
  if (themeSelect) {
    themeSelect.value = 'dark';
  }
  syncThemeInputs('dark');
}

function buildSettingsPayload() {
  const payload = {
    version: 1,
    localStorage: {
      [AUTO_RELOAD_STORAGE_KEY]: localStorage.getItem(AUTO_RELOAD_STORAGE_KEY),
      [AUTO_RELOAD_INTERVAL_KEY]: localStorage.getItem(AUTO_RELOAD_INTERVAL_KEY),
      [AXES_STORAGE_KEY]: localStorage.getItem(AXES_STORAGE_KEY),
      [DEFAULT_CONTROLS_TYPE_STORAGE_KEY]: localStorage.getItem(DEFAULT_CONTROLS_TYPE_STORAGE_KEY),
      [MODEL_SETTINGS_BEHAVIOR_KEY]: localStorage.getItem(MODEL_SETTINGS_BEHAVIOR_KEY),
      [MODEL_DEFAULT_VERSION_KEY]: localStorage.getItem(MODEL_DEFAULT_VERSION_KEY),
      openmfd_cameras_v1: localStorage.getItem('openmfd_cameras_v1'),
      openmfd_theme: localStorage.getItem('openmfd_theme'),
      openmfd_theme_defs_v1: localStorage.getItem('openmfd_theme_defs_v1'),
    },
    lights: lightSystem.getLightState(),
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
  const stored = payload.localStorage || {};
  const apply = {
    general: sections.general !== false,
    theme: sections.theme !== false,
    camera: sections.camera !== false,
    lighting: sections.lighting !== false,
    animation: sections.animation !== false,
  };

  if (apply.general) {
    const keys = [
      AUTO_RELOAD_STORAGE_KEY,
      AUTO_RELOAD_INTERVAL_KEY,
      AXES_STORAGE_KEY,
      DEFAULT_CONTROLS_TYPE_STORAGE_KEY,
      MODEL_SETTINGS_BEHAVIOR_KEY,
      MODEL_DEFAULT_VERSION_KEY,
    ];
    keys.forEach((key) => {
      if (key in stored) {
        const value = stored[key];
        if (value === null || value === undefined) {
          localStorage.removeItem(key);
        } else {
          localStorage.setItem(key, value);
        }
      }
    });

    if (stored[AXES_STORAGE_KEY] !== null && stored[AXES_STORAGE_KEY] !== undefined) {
      applyAxesState(stored[AXES_STORAGE_KEY] !== 'false');
    }

    if (stored[DEFAULT_CONTROLS_TYPE_STORAGE_KEY]) {
      const type = stored[DEFAULT_CONTROLS_TYPE_STORAGE_KEY];
      cameraSystem.setDefaultControlType(type);
      if (defaultControlTypeSelect) defaultControlTypeSelect.value = type;
    }

    if (stored[AUTO_RELOAD_INTERVAL_KEY]) {
      const next = Number.parseInt(stored[AUTO_RELOAD_INTERVAL_KEY], 10);
      if (Number.isFinite(next) && next >= 250) {
        setAutoReloadIntervalMs(next);
        if (autoReloadIntervalInput) autoReloadIntervalInput.value = String(next);
      }
    }

    if (stored[AUTO_RELOAD_STORAGE_KEY] !== null && stored[AUTO_RELOAD_STORAGE_KEY] !== undefined) {
      autoReloadEnabled = stored[AUTO_RELOAD_STORAGE_KEY] !== 'false';
      setAutoReload(autoReloadEnabled);
    }

    if (stored[MODEL_SETTINGS_BEHAVIOR_KEY]) {
      const behavior = stored[MODEL_SETTINGS_BEHAVIOR_KEY];
      if (modelSettingsBehaviorSelect) {
        modelSettingsBehaviorSelect.value = behavior;
      }
      setModelSettingsBehavior(behavior);
    }

    if (stored[MODEL_DEFAULT_VERSION_KEY]) {
      const strategy = stored[MODEL_DEFAULT_VERSION_KEY];
      if (defaultModelVersionSelect) {
        defaultModelVersionSelect.value = strategy;
      }
      setDefaultModelVersionStrategy(strategy);
      modelManager.applyDefaultVersionStrategy();
      if (modelSelector) {
        const snapshot = modelSelector.getSelectionSnapshot();
        modelSelector.applySelectionSnapshot({
          ...snapshot,
          versions: modelManager.getVersionSelections(),
        }, { persist: true });
      }
      modelManager.loadAllModels().then(() => {
        lightSystem.updateDirectionalLightTargets();
      });
    }
  }

  if (apply.theme) {
    let themeState = payload.theme;
    if (!themeState) {
      try {
        const defs = stored.openmfd_theme_defs_v1 ? JSON.parse(stored.openmfd_theme_defs_v1) : null;
        themeState = {
          activeTheme: stored.openmfd_theme || 'dark',
          themes: defs || undefined,
        };
      } catch (e) {
        themeState = null;
      }
    }
    if (themeState) {
      themeManager.setThemeState(themeState);
      if (themeSelect) {
        themeSelect.value = themeState.activeTheme || themeSelect.value;
        syncThemeInputs(themeSelect.value);
      }
    }
  }

  if (apply.camera && stored.openmfd_cameras_v1) {
    localStorage.setItem('openmfd_cameras_v1', stored.openmfd_cameras_v1);
    cameraSystem.initCameraStates();
    cameraSystem.resetCameraHome();
    syncCameraControlSelect();
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
    posX: camPosX,
    posY: camPosY,
    posZ: camPosZ,
    targetX: camTargetX,
    targetY: camTargetY,
    targetZ: camTargetZ,
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
    modelManager.setModelVersionSelections(modelSelector.getSelectionSnapshot().versions);
    modelManager.updateVisibility();
    await modelManager.loadAllModels();
    lightSystem.ensureDefaultLight();
    lightSystem.updateDirectionalLightTargets();
    settingsSystem?.refreshPreviewInfo();
    await checkPreviewSettingsPrompt();
    return;
  }

  if (result.filesChanged) {
    await modelManager.loadAllModels();
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
  modelManager.setModelVersionSelections(modelSelector.getSelectionSnapshot().versions);
  await modelManager.loadAllModels();
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
  await initModels();

  cameraSystem.initCameraStates();
  cameraSystem.resetCameraHome();
  syncCameraControlSelect();

  initAutoReload();
  initResizing();
  document.body.classList.remove('is-loading');
  animate();
}

init();
