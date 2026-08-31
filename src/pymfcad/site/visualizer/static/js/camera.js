import * as THREE from "three";

const CAMERA_STORAGE_KEY = "pymfcad_cameras_v1";
const CAMERA_DEFAULT_COUNT = 0;

export function createCameraSystem({
  scene,
  world,
  controls: initialControls,
  perspectiveCamera,
  orthographicCamera,
  getFrameBox,
  getBoundingBoxScene,
  buildVisibleGroup,
  onCameraChange,
  onCameraModeChange,
  onControlTypeChange,
  onActiveCameraChange,
}) {
  let cameraMode = "perspective";
  let orthoState = null;
  let camera = perspectiveCamera;
  const defaultFov = perspectiveCamera.fov;
  let controls = initialControls;
  let camerasState = [];
  let activeCameraIndex = 0;
  let cameraSlotCount = CAMERA_DEFAULT_COUNT;
  let isApplyingCameraState = false;
  let isHomeMode = false;

  let cameraListEl = null;
  let cameraStripEl = null;
  let cameraModeBtn = null;
  let updateButton = null;
  let updateButtonLabelProvider = null;
  let updateButtonHandler = null;
  let dirtyStateProvider = null;
  let suppressActiveHighlight = false;
  let addButtons = [];
  let removeButton = null;
  let presetButtons = [];
  let inputs = null;

  let allowRoll = true;

  let cameraHelper = null;
  let cameraHelperVisible = false;
  let cameraHelperRef = null;

  let currentDirty = false;
  let currentControlType = "orbit";
  let defaultControlType = "orbit";

  const cameraIcon = new THREE.Group();
  const cameraBody = new THREE.Mesh(
    new THREE.BoxGeometry(0.8, 0.5, 0.35),
    new THREE.MeshBasicMaterial({ color: 0xffaa00 }),
  );
  cameraBody.position.set(0, 0, -0.2);
  const cameraLens = new THREE.Mesh(
    new THREE.ConeGeometry(0.25, 0.6, 16),
    new THREE.MeshBasicMaterial({ color: 0xffdd66 }),
  );
  cameraLens.rotation.x = Math.PI / 2;
  cameraLens.position.set(0, 0, 0.35);
  cameraIcon.add(cameraBody);
  cameraIcon.add(cameraLens);
  cameraIcon.scale.set(1.2, 1.2, 1.2);
  world.add(cameraIcon);

  function toModelSpace(vec) {
    return world.worldToLocal(vec.clone());
  }

  function toSceneSpace(vec) {
    return world.localToWorld(vec.clone());
  }

  function frameModel(object, offset = 1.25) {
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxSize = Math.max(size.x, size.y, size.z);
    const fov = perspectiveCamera.fov * (Math.PI / 180);
    let distance = maxSize / (2 * Math.tan(fov / 2));
    distance *= offset;
    const direction = new THREE.Vector3(0.5, 0.5, 1).normalize();
    perspectiveCamera.position
      .copy(center)
      .add(direction.multiplyScalar(distance));
    controls.target.copy(center);
    controls.update();
    perspectiveCamera.updateProjectionMatrix();
  }

  function updateOrthographicFromBox(box, position, target) {
    const tempCam = new THREE.PerspectiveCamera();
    tempCam.position.copy(position);
    tempCam.up.set(0, 1, 0);
    tempCam.lookAt(target);
    tempCam.updateMatrixWorld(true);
    const view = tempCam.matrixWorldInverse.clone();

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

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    let minZ = Infinity;
    let maxZ = -Infinity;

    corners.forEach((corner) => {
      corner.applyMatrix4(view);
      minX = Math.min(minX, corner.x);
      maxX = Math.max(maxX, corner.x);
      minY = Math.min(minY, corner.y);
      maxY = Math.max(maxY, corner.y);
      minZ = Math.min(minZ, corner.z);
      maxZ = Math.max(maxZ, corner.z);
    });

    const padding = 1.15;
    const width = (maxX - minX) * padding || 1;
    const height = (maxY - minY) * padding || 1;

    const aspect = window.innerWidth / window.innerHeight;
    let viewWidth = width;
    let viewHeight = height;
    if (viewWidth / viewHeight < aspect) {
      viewWidth = viewHeight * aspect;
    } else {
      viewHeight = viewWidth / aspect;
    }

    orthographicCamera.left = -viewWidth / 2;
    orthographicCamera.right = viewWidth / 2;
    orthographicCamera.top = viewHeight / 2;
    orthographicCamera.bottom = -viewHeight / 2;

    const near = Math.max(0.01, -maxZ - width);
    const far = Math.max(near + 1, -minZ + width);
    orthographicCamera.near = near;
    orthographicCamera.far = far;

    orthographicCamera.position.copy(position);
    orthographicCamera.up.set(0, 1, 0);
    orthographicCamera.lookAt(target);
    orthographicCamera.updateProjectionMatrix();

    controls.target.copy(target);
    controls.update();

    orthoState = {
      position: position.clone(),
      target: target.clone(),
      box: box.clone(),
    };
  }

  function resetCamera() {
    perspectiveCamera.fov = 20;
    perspectiveCamera.updateProjectionMatrix();
    const bboxScene = getBoundingBoxScene();
    if (bboxScene && bboxScene.visible) {
      frameModel(bboxScene);
    } else {
      const group = buildVisibleGroup();
      if (group) {
        frameModel(group);
      }
    }

    const box = getFrameBox("orthographic");
    if (box) {
      updateOrthographicFromBox(
        box,
        perspectiveCamera.position,
        controls.target,
      );
    }
    if (currentControlType === "trackball") {
      setCameraPose(camera.position.clone(), controls.target.clone(), 0);
    }
    syncCameraInputs();
    if (!isHomeMode && camerasState[activeCameraIndex]) {
      const nextType = defaultControlType || "orbit";
      if (nextType !== currentControlType) {
        currentControlType = nextType;
        camerasState[activeCameraIndex].controlType = nextType;
        if (onControlTypeChange) {
          onControlTypeChange(nextType);
        }
      } else {
        camerasState[activeCameraIndex].controlType = nextType;
      }
      commitActiveCameraState();
    } else {
      updateActiveCameraStateFromControls();
    }
    if (onCameraChange) onCameraChange();
  }

  function resetCameraHome() {
    isHomeMode = true;
    const bboxScene = getBoundingBoxScene();
    if (bboxScene && bboxScene.visible) {
      frameModel(bboxScene);
    } else {
      const group = buildVisibleGroup();
      if (group) {
        frameModel(group);
      }
    }

    const box = getFrameBox("orthographic");
    if (box) {
      updateOrthographicFromBox(
        box,
        perspectiveCamera.position,
        controls.target,
      );
    }
    if (currentControlType === "trackball") {
      setCameraPose(camera.position.clone(), controls.target.clone(), 0);
    }
    syncCameraInputs();
    currentDirty = false;
    renderCameraList();
    updateUpdateButton();
    if (onCameraChange) onCameraChange();
    if (onActiveCameraChange) onActiveCameraChange();
  }

  function getReferenceUp(viewDir) {
    let baseUp = new THREE.Vector3(0, 1, 0);
    if (Math.abs(viewDir.dot(baseUp)) > 0.999) {
      baseUp = new THREE.Vector3(0, 0, 1);
    }
    let projUp = baseUp
      .clone()
      .sub(viewDir.clone().multiplyScalar(baseUp.dot(viewDir)));
    if (projUp.length() < 1e-6) {
      projUp = new THREE.Vector3(0, 0, 1);
      projUp.sub(viewDir.clone().multiplyScalar(projUp.dot(viewDir)));
    }
    return projUp.normalize();
  }

  function getCameraRollDeg() {
    const viewDir = camera.getWorldDirection(new THREE.Vector3()).normalize();
    if (viewDir.lengthSq() < 1e-6) return 0;
    const baseUp = getReferenceUp(viewDir);
    const camUp = camera.up.clone().normalize();
    const cross = baseUp.clone().cross(camUp);
    const sin = viewDir.dot(cross);
    const cos = baseUp.dot(camUp);
    return THREE.MathUtils.radToDeg(Math.atan2(sin, cos));
  }

  function applyCameraRoll(position, target, rollDeg) {
    const viewDir = target.clone().sub(position).normalize();
    if (viewDir.lengthSq() < 1e-6) return new THREE.Vector3(0, 1, 0);
    const baseUp = getReferenceUp(viewDir);
    const rollRad = THREE.MathUtils.degToRad(rollDeg || 0);
    const quat = new THREE.Quaternion().setFromAxisAngle(viewDir, rollRad);
    return baseUp.clone().applyQuaternion(quat);
  }

  const MAX_PITCH_DEG = 89.9999;
  function normalizeAngleDeg(deg) {
    if (!Number.isFinite(deg)) return 0;
    const wrapped = ((deg % 360) + 360) % 360;
    return wrapped;
  }

  function clampPitchDeg(deg) {
    if (!Number.isFinite(deg)) return 0;
    return Math.max(-MAX_PITCH_DEG, Math.min(MAX_PITCH_DEG, deg));
  }

  function directionToAngles(direction) {
    const dir = direction.clone();
    const length = dir.length();
    if (length < 1e-6) {
      return { yaw: 0, pitch: 0 };
    }
    dir.divideScalar(length);
    const yaw = THREE.MathUtils.radToDeg(Math.atan2(dir.y, dir.x)) + 90;
    const pitch = THREE.MathUtils.radToDeg(
      Math.asin(THREE.MathUtils.clamp(dir.z, -1, 1)),
    );
    return {
      yaw: normalizeAngleDeg(yaw),
      pitch: clampPitchDeg(pitch),
    };
  }

  function anglesToDirection(yawDeg, pitchDeg) {
    const yawRad = THREE.MathUtils.degToRad(normalizeAngleDeg(yawDeg - 90));
    const pitchRad = THREE.MathUtils.degToRad(clampPitchDeg(pitchDeg));
    const cosPitch = Math.cos(pitchRad);
    return new THREE.Vector3(
      cosPitch * Math.cos(yawRad),
      cosPitch * Math.sin(yawRad),
      Math.sin(pitchRad),
    );
  }

  function clampFov(value) {
    if (!Number.isFinite(value)) return defaultFov;
    return Math.min(120, Math.max(5, value));
  }

  function setCameraPose(position, target, rollDeg = 0) {
    const useRoll = allowRoll ? rollDeg : 0;
    const up = allowRoll
      ? applyCameraRoll(position, target, useRoll)
      : new THREE.Vector3(0, 1, 0);

    perspectiveCamera.position.copy(position);
    perspectiveCamera.up.copy(up);
    perspectiveCamera.lookAt(target);
    perspectiveCamera.updateProjectionMatrix();

    orthographicCamera.position.copy(position);
    orthographicCamera.up.copy(up);
    orthographicCamera.lookAt(target);
    orthographicCamera.updateProjectionMatrix();

    controls.target.copy(target);
    controls.update();

    const box = getFrameBox("orthographic");
    if (box) {
      updateOrthographicFromBox(box, position, target);
    }
    if (onCameraChange) onCameraChange();
  }

  function getCurrentCameraState() {
    const pos = toModelSpace(camera.position);
    const target = toModelSpace(controls.target);
    return {
      pos: { x: pos.x, y: pos.y, z: pos.z },
      target: { x: target.x, y: target.y, z: target.z },
      roll: allowRoll ? getCameraRollDeg() : 0,
      fov: perspectiveCamera.fov,
      controlType: currentControlType,
      mode: cameraMode,
    };
  }

  function saveCameraStates() {
    localStorage.setItem(
      CAMERA_STORAGE_KEY,
      JSON.stringify({
        activeIndex: activeCameraIndex,
        cameras: camerasState,
        slotCount: cameraSlotCount,
      }),
    );
  }

  function loadCameraStates() {
    const saved = localStorage.getItem(CAMERA_STORAGE_KEY);
    if (!saved) return false;
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed.cameras)) {
        camerasState = parsed.cameras;
        if (Number.isInteger(parsed.slotCount) && parsed.slotCount > 0) {
          cameraSlotCount = parsed.slotCount;
        } else {
          cameraSlotCount = Math.max(camerasState.length, CAMERA_DEFAULT_COUNT);
        }
        if (Number.isInteger(parsed.activeIndex)) {
          activeCameraIndex = Math.min(
            Math.max(parsed.activeIndex, 0),
            Math.max(cameraSlotCount - 1, 0),
          );
        }
        return camerasState.length > 0;
      }
    } catch (e) {
      // ignore
    }
    return false;
  }

  function updateActiveCameraStateFromControls() {
    if (isHomeMode && !dirtyStateProvider) return;
    if (!dirtyStateProvider && !camerasState[activeCameraIndex]) return;
    currentDirty = isCameraDirty();
    updateUpdateButton();
  }

  function commitActiveCameraState() {
    if (!camerasState[activeCameraIndex]) return;
    camerasState[activeCameraIndex] = getCurrentCameraState();
    saveCameraStates();
    currentDirty = false;
    updateUpdateButton();
  }

  function isCameraDirty() {
    const saved = dirtyStateProvider
      ? dirtyStateProvider()
      : camerasState[activeCameraIndex];
    if (!saved) return false;
    const current = getCurrentCameraState();
    const eps = 1e-4;
    const diff = (a, b) => Math.abs(a - b) > eps;
    const savedRoll = saved.roll ?? 0;
    const savedFov = saved.fov ?? perspectiveCamera.fov;
    return (
      diff(current.pos.x, saved.pos.x) ||
      diff(current.pos.y, saved.pos.y) ||
      diff(current.pos.z, saved.pos.z) ||
      diff(current.target.x, saved.target.x) ||
      diff(current.target.y, saved.target.y) ||
      diff(current.target.z, saved.target.z) ||
      diff(current.roll || 0, savedRoll) ||
      diff(current.fov || perspectiveCamera.fov, savedFov) ||
      (current.controlType || defaultControlType) !==
        (saved.controlType || defaultControlType) ||
      (saved.mode || "perspective") !== (current.mode || "perspective")
    );
  }

  function setDirtyStateProvider(provider) {
    dirtyStateProvider = typeof provider === "function" ? provider : null;
    updateActiveCameraStateFromControls();
  }

  function setSuppressActiveCameraHighlight(suppress) {
    suppressActiveHighlight = !!suppress;
    renderCameraList();
  }

  function getWorldTargetObject() {
    const bboxScene = getBoundingBoxScene();
    if (bboxScene && bboxScene.visible) {
      return bboxScene;
    }
    world.updateMatrixWorld(true);
    const group = buildVisibleGroup();
    if (!group) return null;
    group.matrixAutoUpdate = false;
    group.matrix.copy(world.matrixWorld);
    group.updateMatrixWorld(true);
    return group;
  }

  function getModelCenterWorld() {
    const target = getWorldTargetObject();
    if (!target) return new THREE.Vector3();
    world.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(target);
    return box.getCenter(new THREE.Vector3());
  }

  function setTargetToModelCenter({ persist = true } = {}) {
    const center = getModelCenterWorld();
    controls.target.copy(center);
    controls.update();
    const box = getFrameBox("orthographic");
    if (box) {
      updateOrthographicFromBox(box, camera.position, controls.target);
    }
    syncCameraInputs();
    if (!isHomeMode && camerasState[activeCameraIndex]) {
      if (persist) {
        commitActiveCameraState();
      } else {
        updateActiveCameraStateFromControls();
      }
    } else {
      updateActiveCameraStateFromControls();
    }
    if (onCameraChange) onCameraChange();
  }

  function getTargetObject() {
    return getWorldTargetObject();
  }

  function getFacePresetPosition(face) {
    const target = getTargetObject();
    if (!target) return null;

    const box = new THREE.Box3().setFromObject(target);
    if (!Number.isFinite(box.min.x) || !Number.isFinite(box.max.x)) return null;

    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const fov = (perspectiveCamera.fov * Math.PI) / 180;
    const aspect = window.innerWidth / window.innerHeight;
    const padding = 1.15;

    let width = 1;
    let height = 1;
    let normal = new THREE.Vector3(0, 0, 1);

    switch (face) {
      case "front":
        normal = new THREE.Vector3(0, 0, 1);
        width = size.x;
        height = size.y;
        break;
      case "back":
        normal = new THREE.Vector3(0, 0, -1);
        width = size.x;
        height = size.y;
        break;
      case "left":
        normal = new THREE.Vector3(-1, 0, 0);
        width = size.z;
        height = size.y;
        break;
      case "right":
        normal = new THREE.Vector3(1, 0, 0);
        width = size.z;
        height = size.y;
        break;
      case "top":
        normal = new THREE.Vector3(0, 1, 0);
        width = size.x;
        height = size.z;
        break;
      case "bottom":
        normal = new THREE.Vector3(0, -1, 0);
        width = size.x;
        height = size.z;
        break;
      default:
        return null;
    }

    width = Math.max(width, 1e-6);
    height = Math.max(height, 1e-6);

    const halfHeight = height / 2;
    const halfWidth = width / 2;
    const distanceHeight = halfHeight / Math.tan(fov / 2);
    const distanceWidth = halfWidth / (Math.tan(fov / 2) * aspect);
    const distance = Math.max(distanceHeight, distanceWidth) * padding;

    const position = center.clone().add(normal.multiplyScalar(distance));
    return { position, target: center };
  }

  function applyCameraPreset(face) {
    const pose = getFacePresetPosition(face);
    if (!pose) return;
    const wasHome = isHomeMode;
    if (!wasHome) {
      ensureCameraState(activeCameraIndex);
    }
    setCameraPose(pose.position, pose.target, 0);
    syncCameraInputs();
    renderCameraList();
    updateCameraModeButton();
    if (!wasHome) {
      commitActiveCameraState();
    }
  }

  function ensureCameraState(index) {
    if (!camerasState[index]) {
      camerasState[index] = getCurrentCameraState();
    }
  }

  function applyCameraState(index) {
    const state = camerasState[index];
    if (!state) return;
    const desiredControlType = state.controlType || defaultControlType;
    if (
      desiredControlType &&
      desiredControlType !== currentControlType &&
      onControlTypeChange
    ) {
      onControlTypeChange(desiredControlType);
    }
    currentControlType = desiredControlType;
    isHomeMode = false;
    isApplyingCameraState = true;
    setCameraMode(state.mode || "perspective");
    const pos = new THREE.Vector3(state.pos.x, state.pos.y, state.pos.z);
    const target = new THREE.Vector3(
      state.target.x,
      state.target.y,
      state.target.z,
    );
    setCameraPose(toSceneSpace(pos), toSceneSpace(target), state.roll ?? 0);
    if ((state.mode || "perspective") === "perspective") {
      const nextFov = Number.isFinite(state.fov) ? state.fov : defaultFov;
      perspectiveCamera.fov = clampFov(nextFov);
      perspectiveCamera.updateProjectionMatrix();
    }
    isApplyingCameraState = false;
    updateCameraModeButton();
    syncCameraInputs();
    renderCameraList();
    currentDirty = false;
    updateUpdateButton();
    updateRemoveButton();
    saveCameraStates();
    if (onActiveCameraChange) onActiveCameraChange();
  }

  function renderCameraList() {
    const renderTo = (container) => {
      if (!container) return;
      container.innerHTML = "";
      for (let i = 0; i < cameraSlotCount; i += 1) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "camera-btn";
        btn.textContent = String(i + 1);
        if (
          !isHomeMode &&
          i === activeCameraIndex &&
          !suppressActiveHighlight
        ) {
          btn.classList.add("is-active");
        }
        if (!camerasState[i]) {
          btn.style.opacity = "0.6";
        }
        btn.addEventListener("click", () => {
          isHomeMode = false;
          ensureCameraState(i);
          activeCameraIndex = i;
          applyCameraState(i);
        });
        container.appendChild(btn);
      }
    };
    renderTo(cameraListEl);
    renderTo(cameraStripEl);
    updateRemoveButton();
  }

  function updateUpdateButton() {
    if (!updateButton) return;
    if (
      !dirtyStateProvider &&
      (isHomeMode || !camerasState[activeCameraIndex])
    ) {
      updateButton.style.display = "none";
      return;
    }
    if (currentDirty) {
      const fallbackLabel = `Update Camera ${activeCameraIndex + 1}`;
      const customLabel = updateButtonLabelProvider
        ? updateButtonLabelProvider()
        : null;
      updateButton.textContent = customLabel || fallbackLabel;
      updateButton.style.display = "";
    } else {
      updateButton.style.display = "none";
    }
  }

  function setUpdateButtonLabelProvider(provider) {
    updateButtonLabelProvider =
      typeof provider === "function" ? provider : null;
    updateUpdateButton();
  }

  function setUpdateButtonHandler(handler) {
    updateButtonHandler = typeof handler === "function" ? handler : null;
  }

  function applyExternalCameraState(state) {
    if (!state || !state.pos || !state.target) return;
    const desiredControlType = state.controlType || defaultControlType;
    if (
      desiredControlType &&
      desiredControlType !== currentControlType &&
      onControlTypeChange
    ) {
      onControlTypeChange(desiredControlType);
    }
    currentControlType = desiredControlType;
    isHomeMode = false;
    isApplyingCameraState = true;
    setCameraMode(state.mode || "perspective");
    const pos = new THREE.Vector3(state.pos.x, state.pos.y, state.pos.z);
    const target = new THREE.Vector3(
      state.target.x,
      state.target.y,
      state.target.z,
    );
    setCameraPose(toSceneSpace(pos), toSceneSpace(target), state.roll ?? 0);
    if ((state.mode || "perspective") === "perspective") {
      const nextFov = Number.isFinite(state.fov) ? state.fov : defaultFov;
      perspectiveCamera.fov = clampFov(nextFov);
      perspectiveCamera.updateProjectionMatrix();
    }
    isApplyingCameraState = false;
    updateCameraModeButton();
    syncCameraInputs();
    updateActiveCameraStateFromControls();
  }

  function updateRemoveButton() {
    if (!removeButton) return;
    const hasSelection = !isHomeMode && !!camerasState[activeCameraIndex];
    const canRemove = hasSelection && cameraSlotCount > 1;
    removeButton.disabled = !canRemove;
  }

  function updateCameraModeButton() {
    if (!cameraModeBtn) return;
    const state = camerasState[activeCameraIndex];
    const mode = state?.mode || cameraMode;
    cameraModeBtn.textContent =
      mode === "orthographic" ? "Camera: Ortho" : "Camera: Perspective";
    if (inputs?.fov) {
      inputs.fov.disabled = mode !== "perspective";
    }
  }

  function initCameraStates() {
    const hasSaved = loadCameraStates();
    isHomeMode = true;
    if (!hasSaved) {
      cameraSlotCount = CAMERA_DEFAULT_COUNT;
      camerasState = [];
      activeCameraIndex = 0;
    }
    currentControlType = defaultControlType;
    renderCameraList();
    updateRemoveButton();
    if (onActiveCameraChange) onActiveCameraChange();
    return hasSaved;
  }

  function setCameraMode(nextMode) {
    if (nextMode === cameraMode) return;
    cameraMode = nextMode;
    if (cameraMode === "orthographic") {
      camera = orthographicCamera;
      controls.object = camera;
      const box = getFrameBox("orthographic");
      if (box) {
        updateOrthographicFromBox(
          box,
          perspectiveCamera.position,
          controls.target,
        );
      }
      orthographicCamera.position.copy(perspectiveCamera.position);
      orthographicCamera.up.copy(perspectiveCamera.up);
      orthographicCamera.lookAt(controls.target);
      orthographicCamera.updateProjectionMatrix();
    } else {
      camera = perspectiveCamera;
      controls.object = camera;
      perspectiveCamera.position.copy(orthographicCamera.position);
      perspectiveCamera.up.copy(orthographicCamera.up);
      const savedFov = camerasState[activeCameraIndex]?.fov;
      const nextFov = Number.isFinite(savedFov) ? savedFov : defaultFov;
      perspectiveCamera.fov = clampFov(nextFov);
      perspectiveCamera.lookAt(controls.target);
      perspectiveCamera.updateProjectionMatrix();
    }
    ensureCameraHelper();
    if (onCameraChange) onCameraChange();
    if (onCameraModeChange && !isApplyingCameraState) {
      onCameraModeChange(cameraMode);
    }
    updateUpdateButton();
  }

  function syncCameraInputs() {
    if (!inputs) return;
    const pos = toModelSpace(camera.position);
    const target = toModelSpace(controls.target);
    const direction = pos.clone().sub(target);
    const { yaw, pitch } = directionToAngles(direction);
    if (inputs.yaw) {
      inputs.yaw.value = yaw.toFixed(2);
    }
    if (inputs.pitch) {
      inputs.pitch.value = pitch.toFixed(2);
    }
    inputs.targetX.value = target.x.toFixed(3);
    inputs.targetY.value = target.y.toFixed(3);
    inputs.targetZ.value = target.z.toFixed(3);
    if (inputs.distance) {
      inputs.distance.value = pos.distanceTo(target).toFixed(3);
    }
    if (inputs.roll) {
      const rollValue = allowRoll ? getCameraRollDeg() : 0;
      inputs.roll.value = normalizeAngleDeg(rollValue).toFixed(2);
      inputs.roll.disabled = !allowRoll;
      inputs.roll.title = allowRoll
        ? "Roll (deg)"
        : "Roll is only available in trackball controls.";
    }
    if (inputs.fov) {
      inputs.fov.value = perspectiveCamera.fov.toFixed(1);
      inputs.fov.disabled = cameraMode !== "perspective";
    }
  }

  function evaluateNumericInput(rawValue, fallback) {
    const text = String(rawValue ?? "").trim();
    if (!text) return NaN;
    if (/^[+-]?\d*\.?\d+$/.test(text)) {
      const simple = Number(text);
      return Number.isFinite(simple) ? simple : NaN;
    }
    const base = Number.isFinite(fallback) ? fallback : 0;
    let expr = text
      .replace(/\b(value|v|x|pos)\b/gi, `(${base})`)
      .replace(/\bpi\b/gi, String(Math.PI))
      .replace(/\be\b/gi, String(Math.E));
    if (!/^[0-9+\-*/().\s]*$/.test(expr)) return NaN;
    try {
      const result = Function(`"use strict"; return (${expr});`)();
      return Number.isFinite(result) ? result : NaN;
    } catch (e) {
      return NaN;
    }
  }

  function applyCameraInputs() {
    if (!inputs) return;
    const currentTarget = toModelSpace(controls.target);
    const currentPos = toModelSpace(camera.position);
    const currentDirection = currentPos.clone().sub(currentTarget);
    const { yaw: currentYaw, pitch: currentPitch } =
      directionToAngles(currentDirection);
    const currentDistance = currentPos.distanceTo(currentTarget);

    const target = new THREE.Vector3(
      evaluateNumericInput(inputs.targetX.value, currentTarget.x),
      evaluateNumericInput(inputs.targetY.value, currentTarget.y),
      evaluateNumericInput(inputs.targetZ.value, currentTarget.z),
    );
    const yawDeg = inputs.yaw
      ? evaluateNumericInput(inputs.yaw.value, currentYaw)
      : NaN;
    const pitchDeg = inputs.pitch
      ? evaluateNumericInput(inputs.pitch.value, currentPitch)
      : NaN;
    const distanceValue = inputs.distance
      ? evaluateNumericInput(inputs.distance.value, currentDistance)
      : NaN;
    const rollDeg =
      allowRoll && inputs.roll
        ? evaluateNumericInput(inputs.roll.value, getCameraRollDeg())
        : 0;
    const fovDeg = inputs.fov
      ? evaluateNumericInput(inputs.fov.value, perspectiveCamera.fov)
      : null;

    const distance = Number.isFinite(distanceValue)
      ? Math.max(0, distanceValue)
      : currentDistance;
    if (!Number.isFinite(yawDeg) || !Number.isFinite(pitchDeg)) return;
    const direction = anglesToDirection(yawDeg, pitchDeg);

    if (
      Number.isFinite(target.x) &&
      Number.isFinite(target.y) &&
      Number.isFinite(target.z) &&
      Number.isFinite(distance) &&
      (allowRoll && inputs.roll ? Number.isFinite(rollDeg) : true) &&
      (inputs.fov ? Number.isFinite(fovDeg) : true)
    ) {
      const position = target.clone().add(direction.multiplyScalar(distance));
      setCameraPose(toSceneSpace(position), toSceneSpace(target), rollDeg || 0);
      if (cameraMode === "perspective" && Number.isFinite(fovDeg)) {
        perspectiveCamera.fov = Math.min(120, Math.max(5, fovDeg));
        perspectiveCamera.updateProjectionMatrix();
      }
      if (!isHomeMode && camerasState[activeCameraIndex]) {
        commitActiveCameraState();
      } else {
        updateActiveCameraStateFromControls();
      }
      syncCameraInputs();
    }
  }

  function applyDistanceInput() {
    if (!inputs?.distance) return;
    const currentTarget = toModelSpace(controls.target);
    const currentPos = toModelSpace(camera.position);
    const currentDirection = currentPos.clone().sub(currentTarget);
    const { yaw: currentYaw, pitch: currentPitch } =
      directionToAngles(currentDirection);
    const currentDistance = currentPos.distanceTo(currentTarget);

    const distanceValue = evaluateNumericInput(
      inputs.distance.value,
      currentDistance,
    );
    if (!Number.isFinite(distanceValue) || distanceValue < 0) return;
    if (!inputs?.yaw || !inputs?.pitch) return;

    const target = new THREE.Vector3(
      evaluateNumericInput(inputs.targetX.value, currentTarget.x),
      evaluateNumericInput(inputs.targetY.value, currentTarget.y),
      evaluateNumericInput(inputs.targetZ.value, currentTarget.z),
    );
    if (
      !Number.isFinite(target.x) ||
      !Number.isFinite(target.y) ||
      !Number.isFinite(target.z)
    )
      return;

    const yawDeg = evaluateNumericInput(inputs.yaw.value, currentYaw);
    const pitchDeg = evaluateNumericInput(inputs.pitch.value, currentPitch);
    if (!Number.isFinite(yawDeg) || !Number.isFinite(pitchDeg)) return;

    const direction = anglesToDirection(yawDeg, pitchDeg);
    const nextPos = target.clone().add(direction.multiplyScalar(distanceValue));
    const rollInput = allowRoll
      ? evaluateNumericInput(inputs.roll?.value, getCameraRollDeg())
      : 0;
    const rollDeg = Number.isFinite(rollInput) ? rollInput : 0;
    setCameraPose(toSceneSpace(nextPos), toSceneSpace(target), rollDeg);

    if (!isHomeMode && camerasState[activeCameraIndex]) {
      commitActiveCameraState();
    } else {
      updateActiveCameraStateFromControls();
    }
    if (onCameraChange) onCameraChange();
    syncCameraInputs();
  }

  function setRollEnabled(enabled) {
    allowRoll = !!enabled;
    if (inputs?.roll) {
      inputs.roll.disabled = !allowRoll;
      inputs.roll.title = allowRoll
        ? "Roll (deg)"
        : "Roll is only available in trackball controls.";
      if (!allowRoll) {
        inputs.roll.value = "0";
      }
    }
    if (!allowRoll) {
      const pos = camera.position.clone();
      const target = controls.target.clone();
      setCameraPose(pos, target, 0);
      updateActiveCameraStateFromControls();
    } else {
      syncCameraInputs();
    }
  }

  function addCameraSlot() {
    const nextIndex = cameraSlotCount;
    const typeForNew = currentControlType || defaultControlType;
    if (
      typeForNew &&
      typeForNew !== currentControlType &&
      onControlTypeChange
    ) {
      onControlTypeChange(typeForNew);
    }
    currentControlType = typeForNew;
    camerasState[nextIndex] = getCurrentCameraState();
    cameraSlotCount += 1;
    activeCameraIndex = nextIndex;
    isHomeMode = false;
    currentDirty = false;
    saveCameraStates();
    renderCameraList();
    updateCameraModeButton();
    syncCameraInputs();
    updateUpdateButton();
    updateRemoveButton();
    if (onActiveCameraChange) onActiveCameraChange();
  }

  function removeActiveCameraSlot() {
    if (cameraSlotCount <= 1) return;
    const removeIndex = activeCameraIndex;
    camerasState.splice(removeIndex, 1);
    cameraSlotCount = Math.max(1, cameraSlotCount - 1);
    if (activeCameraIndex >= cameraSlotCount) {
      activeCameraIndex = cameraSlotCount - 1;
    }
    isHomeMode = false;
    ensureCameraState(activeCameraIndex);
    applyCameraState(activeCameraIndex);
    updateRemoveButton();
    if (onActiveCameraChange) onActiveCameraChange();
  }

  function bindCameraUI({
    cameraList,
    cameraStrip,
    cameraModeButton,
    resetButton,
    homeButton,
    centerTargetButton,
    updateButton: updateBtn,
    addButton: addBtn,
    addButtons: addBtns,
    removeButton: removeBtn,
    presetButtons: presetBtns,
    inputFields,
  }) {
    cameraListEl = cameraList;
    cameraStripEl = cameraStrip;
    cameraModeBtn = cameraModeButton;
    updateButton = updateBtn;
    addButtons = [];
    if (addBtn) addButtons.push(addBtn);
    if (Array.isArray(addBtns)) {
      addBtns.forEach((btn) => {
        if (btn) addButtons.push(btn);
      });
    }
    removeButton = removeBtn;
    presetButtons = Array.isArray(presetBtns) ? presetBtns.filter(Boolean) : [];
    inputs = inputFields;

    if (resetButton) {
      resetButton.addEventListener("click", () => {
        resetCamera();
        updateRemoveButton();
      });
    }

    if (homeButton) {
      homeButton.addEventListener("click", () => {
        resetCameraHome();
        updateRemoveButton();
      });
    }

    if (centerTargetButton) {
      centerTargetButton.addEventListener("click", () => {
        setTargetToModelCenter();
      });
    }

    if (updateButton) {
      updateButton.addEventListener("click", () => {
        if (updateButtonHandler && updateButtonHandler()) {
          return;
        }
        commitActiveCameraState();
      });
      updateUpdateButton();
    }

    addButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        addCameraSlot();
      });
    });

    if (removeButton) {
      removeButton.addEventListener("click", () => {
        removeActiveCameraSlot();
      });
    }

    if (cameraModeBtn) {
      cameraModeBtn.addEventListener("click", () => {
        const current = camerasState[activeCameraIndex]?.mode || cameraMode;
        const next =
          current === "orthographic" ? "perspective" : "orthographic";
        setCameraMode(next);
        if (camerasState[activeCameraIndex]) {
          camerasState[activeCameraIndex].mode = next;
          saveCameraStates();
        }
        updateCameraModeButton();
      });
    }

    presetButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const face = btn.getAttribute("data-camera-preset");
        if (face) {
          applyCameraPreset(face);
        }
      });
    });

    if (inputs) {
      const commitOnEnter = (handler) => (event) => {
        if (event.key === "Enter") {
          handler();
        }
      };
      [
        inputs.yaw,
        inputs.pitch,
        inputs.targetX,
        inputs.targetY,
        inputs.targetZ,
        inputs.roll,
        inputs.fov,
      ]
        .filter(Boolean)
        .forEach((input) => {
          input.addEventListener("change", applyCameraInputs);
          input.addEventListener("keydown", commitOnEnter(applyCameraInputs));
        });

      if (inputs.distance) {
        inputs.distance.addEventListener("change", applyDistanceInput);
        inputs.distance.addEventListener(
          "keydown",
          commitOnEnter(applyDistanceInput),
        );
      }
    }

    updateRemoveButton();
  }

  function setActiveCameraControlType(type) {
    if (isHomeMode || !camerasState[activeCameraIndex]) return;
    const nextType = type || defaultControlType;
    camerasState[activeCameraIndex].controlType = nextType;
    currentControlType = nextType;
    saveCameraStates();
    if (onControlTypeChange) {
      onControlTypeChange(nextType);
    }
    updateUpdateButton();
  }

  function updateCameraIcon() {
    const camWorldPos = camera.position.clone();
    const camWorldTarget = controls.target.clone();
    const camLocalPos = world.worldToLocal(camWorldPos);
    cameraIcon.position.copy(camLocalPos);
    cameraIcon.lookAt(camWorldTarget);
  }

  function ensureCameraHelper() {
    if (cameraHelperRef !== camera) {
      if (cameraHelper) {
        scene.remove(cameraHelper);
      }
      cameraHelper = new THREE.CameraHelper(camera);
      cameraHelper.visible = cameraHelperVisible;
      scene.add(cameraHelper);
      cameraHelperRef = camera;
    }
  }

  function setCameraHelperVisible(isVisible) {
    cameraHelperVisible = isVisible;
    cameraIcon.visible = isVisible;
    ensureCameraHelper();
    if (cameraHelper) {
      cameraHelper.visible = isVisible;
      cameraHelper.update();
    }
  }

  function updateCameraHelper() {
    ensureCameraHelper();
    if (cameraHelper) {
      cameraHelper.update();
    }
  }

  function handleResize() {
    perspectiveCamera.aspect = window.innerWidth / window.innerHeight;
    perspectiveCamera.updateProjectionMatrix();
    if (cameraMode === "orthographic" && orthoState) {
      updateOrthographicFromBox(
        orthoState.box,
        orthoState.position,
        orthoState.target,
      );
    }
  }

  const handleControlsChange = () => {
    if (isApplyingCameraState) return;
    updateActiveCameraStateFromControls();
    if (onCameraChange) onCameraChange();
  };

  if (controls && controls.addEventListener) {
    controls.addEventListener("change", handleControlsChange);
  }

  return {
    setControls: (nextControls) => {
      if (!nextControls || nextControls === controls) return;
      const prevTarget = controls?.target ? controls.target.clone() : null;
      if (controls && controls.removeEventListener) {
        controls.removeEventListener("change", handleControlsChange);
      }
      controls = nextControls;
      if (prevTarget && controls.target) {
        controls.target.copy(prevTarget);
      }
      if (controls && controls.addEventListener) {
        controls.addEventListener("change", handleControlsChange);
      }
      if (controls && controls.update) {
        controls.update();
      }
      updateActiveCameraStateFromControls();
    },
    getCamera: () => camera,
    getCameraMode: () => cameraMode,
    getCameraState: getCurrentCameraState,
    resetCamera,
    resetCameraHome,
    setCameraMode,
    setCameraPose,
    initCameraStates,
    renderCameraList,
    updateCameraModeButton,
    syncCameraInputs,
    bindCameraUI,
    updateCameraIcon,
    updateActiveCameraStateFromControls,
    refreshUpdateButton: updateUpdateButton,
    setUpdateButtonLabelProvider,
    setUpdateButtonHandler,
    setDirtyStateProvider,
    setSuppressActiveCameraHighlight,
    applyExternalCameraState,
    setCameraHelperVisible,
    getCameraHelperVisible: () => cameraHelperVisible,
    updateCameraHelper,
    handleResize,
    setTargetToModelCenter,
    commitActiveCameraState,
    setRollEnabled,
    setCurrentControlType: (type) => {
      currentControlType = type || defaultControlType;
    },
    getCurrentControlType: () => currentControlType,
    setDefaultControlType: (type) => {
      defaultControlType = type || "orbit";
    },
    getDefaultControlType: () => defaultControlType,
    getActiveCameraState: () => camerasState[activeCameraIndex] || null,
    isHomeMode: () => isHomeMode,
    setActiveCameraControlType,
  };
}
