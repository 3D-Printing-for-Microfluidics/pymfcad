import * as THREE from '../lib/three/three.module.js';

export function createLightSystem({ scene, world, cameraSystem, previewSystem, getModelCenterModel }) {
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
  world.add(ambientLight);

  const directionalLights = [];
  const directionalHelpers = [];
  let defaultLightInitialized = false;
  let lightHelpersVisible = false;
  let activeDirLightIndex = 0;

  let dialogEl = null;
  let dialogCloseBtn = null;
  let dialogOpenBtn = null;
  let cameraListEl = null;
  let cameraStripEl = null;

  let ambientColorInput = null;
  let ambientIntensityInput = null;
  let directionalLightsList = null;
  let addDirLightBtn = null;
  let removeDirLightBtn = null;


  function createDirectionalHelper(light) {
    if (light.isSpotLight) {
      const helper = new THREE.SpotLightHelper(light);
      helper.visible = lightHelpersVisible;
      scene.add(helper);
      return helper;
    }
    const helper = new THREE.DirectionalLightHelper(light, 2);
    helper.visible = lightHelpersVisible;
    scene.add(helper);
    return helper;
  }

  function updateDirectionalHelper(helper, light) {
    if (helper.setColor) {
      helper.setColor(light.color);
    } else if (helper.material && helper.material.color) {
      helper.material.color.copy(light.color);
    }
    helper.update();
  }

  function addDirectionalLight(options = {}) {
    const type = options.type || 'directional';
    const light = type === 'spot'
      ? new THREE.SpotLight(options.color ?? 0xffffff, options.intensity ?? 1.0)
      : new THREE.DirectionalLight(options.color ?? 0xffffff, options.intensity ?? 1.0);
    const modelCenter = getModelCenterModel();
    const offset = options.offset ?? new THREE.Vector3(10, 10, 10);
    const pos = options.position ?? modelCenter.clone().add(offset);
    light.position.copy(pos);
    world.add(light);
    world.add(light.target);
    light.target.position.copy(getModelCenterModel());
    if (light.isSpotLight) {
      if (Number.isFinite(options.distance)) light.distance = options.distance;
      if (Number.isFinite(options.angle)) light.angle = options.angle;
      if (Number.isFinite(options.penumbra)) light.penumbra = options.penumbra;
      if (Number.isFinite(options.decay)) light.decay = options.decay;
    }
    const helper = createDirectionalHelper(light);
    directionalLights.push(light);
    directionalHelpers.push(helper);
    activeDirLightIndex = directionalLights.length - 1;
    return light;
  }

  function removeDirectionalLight(index) {
    const light = directionalLights[index];
    const helper = directionalHelpers[index];
    if (helper) {
      scene.remove(helper);
      if (helper.dispose) helper.dispose();
    }
    if (light) {
      if (light.target) world.remove(light.target);
      world.remove(light);
    }
    directionalLights.splice(index, 1);
    directionalHelpers.splice(index, 1);
    if (directionalLights.length === 0) {
      activeDirLightIndex = 0;
      return;
    }
    if (activeDirLightIndex >= directionalLights.length) {
      activeDirLightIndex = directionalLights.length - 1;
    }
  }

  function clearDirectionalLights() {
    for (let i = directionalLights.length - 1; i >= 0; i -= 1) {
      removeDirectionalLight(i);
    }
    directionalLights.length = 0;
    directionalHelpers.length = 0;
    activeDirLightIndex = 0;
  }

  function updateRemoveDirLightButton() {
    if (!removeDirLightBtn) return;
    const hasSelection = directionalLights.length > 0;
    const canRemove = hasSelection && directionalLights.length > 1;
    removeDirLightBtn.disabled = !canRemove;
  }

  function updateDirectionalLightTargets() {
    const modelCenter = getModelCenterModel();
    directionalLights.forEach((light, index) => {
      light.target.position.copy(modelCenter);
      const helper = directionalHelpers[index];
      if (helper) {
        updateDirectionalHelper(helper, light);
      }
    });
  }

  function ensureDefaultLight() {
    if (defaultLightInitialized) return;
    defaultLightInitialized = true;
    addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10) });
  }

  function toHexColor(color) {
    return `#${color.getHexString()}`;
  }

  function setDialogOpen(isOpen) {
    if (!dialogEl) return;
    dialogEl.classList.toggle('is-open', isOpen);
    lightHelpersVisible = isOpen;
    directionalHelpers.forEach((helper) => {
      helper.visible = isOpen;
      helper.update();
    });
    cameraSystem.setCameraHelperVisible(isOpen);
    if (previewSystem) {
      previewSystem.setOpen(isOpen);
    }
  }

  function renderDirectionalLightsList() {
    if (!directionalLightsList) return;
    directionalLightsList.innerHTML = '';
    if (directionalLights.length === 0) {
      updateRemoveDirLightButton();
      return;
    }

    const buttonsRow = document.createElement('div');
    buttonsRow.className = 'light-list';
    directionalLights.forEach((_, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'light-btn';
      btn.textContent = String(index + 1);
      if (index === activeDirLightIndex) {
        btn.classList.add('is-active');
      }
      btn.addEventListener('click', () => {
        activeDirLightIndex = index;
        renderDirectionalLightsList();
      });
      buttonsRow.appendChild(btn);
    });
    directionalLightsList.appendChild(buttonsRow);

    updateRemoveDirLightButton();

    const light = directionalLights[activeDirLightIndex];
    if (!light) return;
    const modelCenter = getModelCenterModel();

    const editor = document.createElement('div');
    editor.className = 'dir-light-row';

    const gridPrimary = document.createElement('div');
    gridPrimary.className = 'input-grid';

    const colorLabel = document.createElement('label');
    colorLabel.textContent = 'Color';
    const colorInput = document.createElement('input');
    colorInput.type = 'color';
    colorInput.value = toHexColor(light.color);
    colorLabel.appendChild(colorInput);
    gridPrimary.appendChild(colorLabel);

    const intensityLabel = document.createElement('label');
    intensityLabel.textContent = 'Intensity';
    const intensityInput = document.createElement('input');
    intensityInput.type = 'number';
    intensityInput.step = '0.1';
    intensityInput.min = '0';
    intensityInput.value = light.intensity.toFixed(3);
    intensityLabel.appendChild(intensityInput);
    gridPrimary.appendChild(intensityLabel);

    const typeLabel = document.createElement('label');
    typeLabel.textContent = 'Type';
    const typeSelect = document.createElement('select');
    typeSelect.innerHTML = '<option value="directional">Directional</option><option value="spot">Spot</option>';
    typeSelect.value = light.isSpotLight ? 'spot' : 'directional';
    typeLabel.appendChild(typeSelect);
    gridPrimary.appendChild(typeLabel);

    const gridPosition = document.createElement('div');
    gridPosition.className = 'input-grid';

    const posXLabel = document.createElement('label');
    posXLabel.textContent = 'Pos X';
    const posXInput = document.createElement('input');
    posXInput.type = 'number';
    posXInput.step = '0.1';
    posXInput.value = (light.position.x - modelCenter.x).toFixed(3);
    posXLabel.appendChild(posXInput);
    gridPosition.appendChild(posXLabel);

    const posYLabel = document.createElement('label');
    posYLabel.textContent = 'Pos Y';
    const posYInput = document.createElement('input');
    posYInput.type = 'number';
    posYInput.step = '0.1';
    posYInput.value = (light.position.y - modelCenter.y).toFixed(3);
    posYLabel.appendChild(posYInput);
    gridPosition.appendChild(posYLabel);

    const posZLabel = document.createElement('label');
    posZLabel.textContent = 'Pos Z';
    const posZInput = document.createElement('input');
    posZInput.type = 'number';
    posZInput.step = '0.1';
    posZInput.value = (light.position.z - modelCenter.z).toFixed(3);
    posZLabel.appendChild(posZInput);
    gridPosition.appendChild(posZLabel);

    editor.appendChild(gridPrimary);
    editor.appendChild(gridPosition);

    const gridSpot = document.createElement('div');
    gridSpot.className = 'input-grid';

    const distanceLabel = document.createElement('label');
    distanceLabel.textContent = 'Distance';
    const distanceInput = document.createElement('input');
    distanceInput.type = 'number';
    distanceInput.step = '0.1';
    distanceInput.min = '0';
    distanceInput.value = light.isSpotLight ? light.distance.toFixed(3) : '0';
    distanceLabel.appendChild(distanceInput);
    gridSpot.appendChild(distanceLabel);

    const angleLabel = document.createElement('label');
    angleLabel.textContent = 'Angle (deg)';
    const angleInput = document.createElement('input');
    angleInput.type = 'number';
    angleInput.step = '1';
    angleInput.min = '1';
    angleInput.max = '90';
    angleInput.value = light.isSpotLight
      ? THREE.MathUtils.radToDeg(light.angle).toFixed(1)
      : '30';
    angleLabel.appendChild(angleInput);
    gridSpot.appendChild(angleLabel);

    const penumbraLabel = document.createElement('label');
    penumbraLabel.textContent = 'Penumbra';
    const penumbraInput = document.createElement('input');
    penumbraInput.type = 'number';
    penumbraInput.step = '0.01';
    penumbraInput.min = '0';
    penumbraInput.max = '1';
    penumbraInput.value = light.isSpotLight ? light.penumbra.toFixed(2) : '0';
    penumbraLabel.appendChild(penumbraInput);
    gridSpot.appendChild(penumbraLabel);

    const decayLabel = document.createElement('label');
    decayLabel.textContent = 'Decay';
    const decayInput = document.createElement('input');
    decayInput.type = 'number';
    decayInput.step = '0.1';
    decayInput.min = '0';
    decayInput.value = light.isSpotLight ? light.decay.toFixed(2) : '1';
    decayLabel.appendChild(decayInput);
    gridSpot.appendChild(decayLabel);

    editor.appendChild(gridSpot);

    const syncSpotVisibility = () => {
      gridSpot.style.display = light.isSpotLight ? '' : 'none';
    };
    syncSpotVisibility();


    function updateLight() {
      const nextIntensity = parseFloat(intensityInput.value);
      const posX = parseFloat(posXInput.value);
      const posY = parseFloat(posYInput.value);
      const posZ = parseFloat(posZInput.value);
      if (Number.isFinite(nextIntensity)) {
        light.intensity = Math.max(0, nextIntensity);
      }
      if (Number.isFinite(posX) && Number.isFinite(posY) && Number.isFinite(posZ)) {
        light.position.set(modelCenter.x + posX, modelCenter.y + posY, modelCenter.z + posZ);
      }
      light.color.set(colorInput.value);
      light.target.position.copy(modelCenter);
      if (light.isSpotLight) {
        const dist = parseFloat(distanceInput.value);
        const angleDeg = parseFloat(angleInput.value);
        const pen = parseFloat(penumbraInput.value);
        const decay = parseFloat(decayInput.value);
        if (Number.isFinite(dist)) light.distance = Math.max(0, dist);
        if (Number.isFinite(angleDeg)) {
          const angleRad = THREE.MathUtils.degToRad(Math.min(90, Math.max(1, angleDeg)));
          light.angle = angleRad;
        }
        if (Number.isFinite(pen)) light.penumbra = Math.min(1, Math.max(0, pen));
        if (Number.isFinite(decay)) light.decay = Math.max(0, decay);
      }
      const helper = directionalHelpers[activeDirLightIndex];
      if (helper) {
        updateDirectionalHelper(helper, light);
      }
    }

    colorInput.addEventListener('input', updateLight);
    intensityInput.addEventListener('input', updateLight);
    posXInput.addEventListener('input', updateLight);
    posYInput.addEventListener('input', updateLight);
    posZInput.addEventListener('input', updateLight);
    distanceInput.addEventListener('input', updateLight);
    angleInput.addEventListener('input', updateLight);
    penumbraInput.addEventListener('input', updateLight);
    decayInput.addEventListener('input', updateLight);

    typeSelect.addEventListener('change', () => {
      const nextType = typeSelect.value;
      const current = directionalLights[activeDirLightIndex];
      if (!current) return;
      const offset = current.position.clone().sub(modelCenter);
      const snapshot = {
        color: current.color.getHex(),
        intensity: current.intensity,
        distance: current.isSpotLight ? current.distance : parseFloat(distanceInput.value),
        angle: current.isSpotLight ? current.angle : THREE.MathUtils.degToRad(parseFloat(angleInput.value)),
        penumbra: current.isSpotLight ? current.penumbra : parseFloat(penumbraInput.value),
        decay: current.isSpotLight ? current.decay : parseFloat(decayInput.value),
        offset,
      };
      removeDirectionalLight(activeDirLightIndex);
      addDirectionalLight({
        type: nextType,
        color: snapshot.color,
        intensity: snapshot.intensity,
        distance: snapshot.distance,
        angle: snapshot.angle,
        penumbra: snapshot.penumbra,
        decay: snapshot.decay,
        offset,
      });
      renderDirectionalLightsList();
    });
    directionalLightsList.appendChild(editor);
  }

  function getLightState() {
    const modelCenter = getModelCenterModel();
    return {
      ambient: {
        color: toHexColor(ambientLight.color),
        intensity: ambientLight.intensity,
      },
      directional: directionalLights.map((light) => {
        const offset = light.position.clone().sub(modelCenter);
        return {
          type: light.isSpotLight ? 'spot' : 'directional',
          color: toHexColor(light.color),
          intensity: light.intensity,
          offset: { x: offset.x, y: offset.y, z: offset.z },
          distance: light.isSpotLight ? light.distance : undefined,
          angle: light.isSpotLight ? light.angle : undefined,
          penumbra: light.isSpotLight ? light.penumbra : undefined,
          decay: light.isSpotLight ? light.decay : undefined,
        };
      }),
    };
  }

  function applyLightState(state) {
    if (!state || typeof state !== 'object') return;
    if (state.ambient) {
      if (state.ambient.color) {
        ambientLight.color.set(state.ambient.color);
      }
      if (Number.isFinite(state.ambient.intensity)) {
        ambientLight.intensity = Math.max(0, state.ambient.intensity);
      }
    }

    clearDirectionalLights();
    const modelCenter = getModelCenterModel();
    const dirList = Array.isArray(state.directional) ? state.directional : [];
    if (dirList.length === 0) {
      addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10) });
    } else {
      dirList.forEach((item) => {
        const offset = item?.offset || { x: 10, y: 10, z: 10 };
        addDirectionalLight({
          type: item?.type || 'directional',
          color: item?.color ? new THREE.Color(item.color) : 0xffffff,
          intensity: Number.isFinite(item?.intensity) ? item.intensity : 1.0,
          offset: new THREE.Vector3(offset.x, offset.y, offset.z),
          position: modelCenter.clone().add(new THREE.Vector3(offset.x, offset.y, offset.z)),
          distance: Number.isFinite(item?.distance) ? item.distance : undefined,
          angle: Number.isFinite(item?.angle) ? item.angle : undefined,
          penumbra: Number.isFinite(item?.penumbra) ? item.penumbra : undefined,
          decay: Number.isFinite(item?.decay) ? item.decay : undefined,
        });
      });
    }
    syncLightInputs();
  }

  function resetLights() {
    ambientLight.color.set(0xffffff);
    ambientLight.intensity = 1.0;
    clearDirectionalLights();
    addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10) });
    syncLightInputs();
  }

  function syncLightInputs() {
    if (ambientColorInput) ambientColorInput.value = toHexColor(ambientLight.color);
    if (ambientIntensityInput) ambientIntensityInput.value = ambientLight.intensity.toFixed(3);
    const modelCenter = getModelCenterModel();
    directionalLights.forEach((light, index) => {
      light.target.position.copy(modelCenter);
      const helper = directionalHelpers[index];
      if (helper) {
        updateDirectionalHelper(helper, light);
      }
    });
    renderDirectionalLightsList();
  }

  function bindLightUI({
    dialog,
    openBtn,
    closeBtn,
    cameraList,
    cameraStrip,
    ambientColor,
    ambientIntensity,
    directionalList,
    addDirLight,
    removeDirLight,
    onOpen,
  }) {
    dialogEl = dialog;
    dialogOpenBtn = openBtn;
    dialogCloseBtn = closeBtn;
    cameraListEl = cameraList;
    cameraStripEl = cameraStrip;

    ambientColorInput = ambientColor;
    ambientIntensityInput = ambientIntensity;
    directionalLightsList = directionalList;
    addDirLightBtn = addDirLight;
    removeDirLightBtn = removeDirLight;

    if (ambientColorInput) {
      ambientColorInput.addEventListener('input', () => {
        ambientLight.color.set(ambientColorInput.value);
      });
    }

    if (ambientIntensityInput) {
      ambientIntensityInput.addEventListener('input', () => {
        const next = parseFloat(ambientIntensityInput.value);
        if (Number.isFinite(next)) {
          ambientLight.intensity = Math.max(0, next);
        }
      });
    }

    if (addDirLightBtn) {
      addDirLightBtn.addEventListener('click', () => {
        addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10) });
        renderDirectionalLightsList();
      });
    }

    if (removeDirLightBtn) {
      removeDirLightBtn.addEventListener('click', () => {
        if (directionalLights.length <= 1) return;
        removeDirectionalLight(activeDirLightIndex);
        renderDirectionalLightsList();
      });
    }

    if (openBtn && dialogEl) {
      openBtn.addEventListener('click', () => {
        cameraSystem.syncCameraInputs();
        syncLightInputs();
        cameraSystem.renderCameraList();
        cameraSystem.updateCameraModeButton();
        if (onOpen) {
          onOpen();
        }
        setDialogOpen(true);
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        setDialogOpen(false);
      });
    }

    if (dialogEl) {
      dialogEl.addEventListener('click', (event) => {
        if (event.target === dialogEl) {
          setDialogOpen(false);
        }
      });
    }
  }

  return {
    ambientLight,
    ensureDefaultLight,
    updateDirectionalLightTargets,
    syncLightInputs,
    bindLightUI,
    renderDirectionalLightsList,
    setDialogOpen,
    getLightState,
    applyLightState,
    resetLights,
  };
}
