import * as THREE from "three";
import { OrbitControls } from "../../../static/js/controls/OrbitControls.js";

export function createPreviewSystem({
  scene,
  world,
  controls: initialControls,
  cameraSystem,
  buildVisibleGroup,
}) {
  let controls = initialControls;
  let buildVisibleGroupRef = buildVisibleGroup || null;
  let worldRef = world || null;
  let lightSystemRef = null;
  let getActiveTabRef = null;
  let dialogViewer = null;
  let previewRenderer = null;
  let previewCamera = null;
  let previewControls = null;
  let isOpen = false;
  let isRaycastBound = false;
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function updateHelperVisibility() {
    const activeTab = getActiveTabRef ? getActiveTabRef() : null;
    const showCameraHelpers = isOpen && activeTab === "camera";
    const showLightHelpers = isOpen && activeTab === "lights";
    if (cameraSystem?.setCameraHelperVisible) {
      cameraSystem.setCameraHelperVisible(showCameraHelpers);
    }
    if (lightSystemRef?.setHelpersVisible) {
      lightSystemRef.setHelpersVisible(showLightHelpers);
    }
  }

  function ensureRenderer() {
    if (!dialogViewer) return;
    if (!previewRenderer) {
      previewRenderer = new THREE.WebGLRenderer({ antialias: true });
      previewRenderer.setPixelRatio(window.devicePixelRatio || 1);
      dialogViewer.appendChild(previewRenderer.domElement);
      previewRenderer.domElement.style.display = "block";
      previewRenderer.domElement.style.width = "100%";
      previewRenderer.domElement.style.height = "100%";
      previewCamera = new THREE.PerspectiveCamera(40, 1, 0.1, 5000);
      previewControls = new OrbitControls(
        previewCamera,
        previewRenderer.domElement,
      );
      previewControls.enableDamping = true;
      previewControls.dampingFactor = 0.08;
      bindRaycastEvents();
    } else if (previewRenderer.domElement.parentElement !== dialogViewer) {
      dialogViewer.appendChild(previewRenderer.domElement);
    }
  }

  function bindRaycastEvents() {
    if (isRaycastBound || !previewRenderer) return;
    previewRenderer.domElement.addEventListener("dblclick", (event) => {
      if (!previewCamera || !buildVisibleGroupRef || !worldRef) return;
      const activeTab = getActiveTabRef ? getActiveTabRef() : null;
      if (activeTab !== "camera" && activeTab !== "lights") return;

      const rect = previewRenderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(pointer, previewCamera);
      const targetGroup = buildVisibleGroupRef();
      if (!targetGroup) return;
      targetGroup.matrixAutoUpdate = false;
      targetGroup.matrix.copy(worldRef.matrixWorld);
      targetGroup.updateMatrixWorld(true);
      const hits = raycaster.intersectObject(targetGroup, true);
      const hit = hits.find((entry) => entry.object?.isMesh);
      if (!hit) return;

      if (activeTab === "camera") {
        const camera = cameraSystem.getCamera();
        if (!camera) return;
        const roll = cameraSystem.getCameraState().roll || 0;
        cameraSystem.setCameraPose(
          camera.position.clone(),
          hit.point.clone(),
          roll,
        );
        syncFromMain();
      } else if (activeTab === "lights") {
        lightSystemRef?.setActiveLightTarget?.(hit.point.clone());
      }
    });
    isRaycastBound = true;
  }

  function bindViewer(viewerEl) {
    dialogViewer = viewerEl;
    if (isOpen) {
      ensureRenderer();
      syncFromMain();
      updateSize();
    }
    updateHelperVisibility();
  }

  function updateSize() {
    if (!previewRenderer || !previewCamera || !dialogViewer) return;
    const rect = dialogViewer.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    previewRenderer.setSize(width, height);
    previewCamera.aspect = width / height;
    previewCamera.updateProjectionMatrix();
  }

  function syncFromMain() {
    if (!previewCamera || !previewControls) return;
    const activeCamera = cameraSystem.getCamera();
    previewCamera.position.copy(activeCamera.position);
    if (controls?.target) {
      previewControls.target.copy(controls.target);
    }
    previewCamera.lookAt(previewControls.target);
    previewCamera.updateProjectionMatrix();
    previewControls.update();
    cameraSystem.updateCameraHelper();
  }

  function setOpen(open) {
    isOpen = open;
    if (open) {
      ensureRenderer();
      syncFromMain();
      updateSize();
    }
    updateHelperVisibility();
  }

  function render() {
    if (!isOpen || !previewRenderer || !previewCamera || !previewControls)
      return;
    previewControls.update();
    cameraSystem.updateCameraHelper();
    previewRenderer.render(scene, previewCamera);
  }

  return {
    bindViewer,
    updateSize,
    syncFromMain,
    setOpen,
    render,
    setInteractionDependencies: ({
      lightSystem,
      getActiveTab,
      buildVisibleGroup: buildGroup,
      world: worldInput,
    }) => {
      if (lightSystem) lightSystemRef = lightSystem;
      if (typeof getActiveTab === "function") getActiveTabRef = getActiveTab;
      if (buildGroup) buildVisibleGroupRef = buildGroup;
      if (worldInput) worldRef = worldInput;
      updateHelperVisibility();
    },
    setControls: (nextControls) => {
      controls = nextControls;
      if (isOpen) {
        syncFromMain();
      }
    },
  };
}
