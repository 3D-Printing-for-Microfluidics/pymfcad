import * as THREE from '../lib/three/three.module.js';

export function createLightSystem({ scene, world, cameraSystem, previewSystem, getModelCenterModel }) {
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
  world.add(ambientLight);

  const directionalLights = [];
  const directionalHelpers = [];
  const transitionExtras = new Map();
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
  let allowStructureEdit = true;
  let onStructureChange = null;


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
    const targetOffset = options.targetOffset ?? new THREE.Vector3(0, 0, 0);
    const pos = options.position ?? modelCenter.clone().add(offset);
    light.position.copy(pos);
    world.add(light);
    world.add(light.target);
    light.userData.targetOffset = targetOffset.clone ? targetOffset.clone() : new THREE.Vector3(targetOffset.x || 0, targetOffset.y || 0, targetOffset.z || 0);
    light.target.position.copy(modelCenter.clone().add(light.userData.targetOffset));
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
    removeDirLightBtn.disabled = !allowStructureEdit || !canRemove;
    removeDirLightBtn.title = allowStructureEdit
      ? 'Remove Directional Light'
      : 'Light structure can only be edited in keyframe 1.';
  }

  function setStructureEditable(isEditable) {
    allowStructureEdit = !!isEditable;
    if (addDirLightBtn) {
      addDirLightBtn.disabled = !allowStructureEdit;
      addDirLightBtn.title = allowStructureEdit
        ? 'Add Directional Light'
        : 'Light structure can only be edited in keyframe 1.';
    }
    updateRemoveDirLightButton();
    renderDirectionalLightsList();
  }

  function setStructureChangeCallback(callback) {
    onStructureChange = typeof callback === 'function' ? callback : null;
  }

  function updateDirectionalLightTargets() {
    const modelCenter = getModelCenterModel();
    directionalLights.forEach((light, index) => {
      const targetOffset = light.userData?.targetOffset || new THREE.Vector3(0, 0, 0);
      light.target.position.copy(modelCenter.clone().add(targetOffset));
      const helper = directionalHelpers[index];
      if (helper) {
        updateDirectionalHelper(helper, light);
      }
    });
  }

  function ensureDefaultLight() {
    if (defaultLightInitialized) return;
    defaultLightInitialized = true;
    addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10), intensity: 1.5 });
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
    typeSelect.disabled = !allowStructureEdit;
    if (!allowStructureEdit) {
      typeSelect.title = 'Light type can only be changed in keyframe 1.';
    }
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

    const targetOffset = light.userData?.targetOffset || new THREE.Vector3(0, 0, 0);
    const targetXLabel = document.createElement('label');
    targetXLabel.textContent = 'Target X';
    const targetXInput = document.createElement('input');
    targetXInput.type = 'number';
    targetXInput.step = '0.1';
    targetXInput.value = targetOffset.x.toFixed(3);
    targetXLabel.appendChild(targetXInput);
    gridSpot.appendChild(targetXLabel);

    const targetYLabel = document.createElement('label');
    targetYLabel.textContent = 'Target Y';
    const targetYInput = document.createElement('input');
    targetYInput.type = 'number';
    targetYInput.step = '0.1';
    targetYInput.value = targetOffset.y.toFixed(3);
    targetYLabel.appendChild(targetYInput);
    gridSpot.appendChild(targetYLabel);

    const targetZLabel = document.createElement('label');
    targetZLabel.textContent = 'Target Z';
    const targetZInput = document.createElement('input');
    targetZInput.type = 'number';
    targetZInput.step = '0.1';
    targetZInput.value = targetOffset.z.toFixed(3);
    targetZLabel.appendChild(targetZInput);
    gridSpot.appendChild(targetZLabel);

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
      if (light.isSpotLight) {
        const tX = parseFloat(targetXInput.value);
        const tY = parseFloat(targetYInput.value);
        const tZ = parseFloat(targetZInput.value);
        const nextTargetOffset = new THREE.Vector3(
          Number.isFinite(tX) ? tX : 0,
          Number.isFinite(tY) ? tY : 0,
          Number.isFinite(tZ) ? tZ : 0
        );
        light.userData.targetOffset = nextTargetOffset;
        light.target.position.copy(modelCenter.clone().add(nextTargetOffset));
      } else {
        light.userData.targetOffset = new THREE.Vector3(0, 0, 0);
        light.target.position.copy(modelCenter);
      }
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
    targetXInput.addEventListener('input', updateLight);
    targetYInput.addEventListener('input', updateLight);
    targetZInput.addEventListener('input', updateLight);

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
        targetOffset: current.userData?.targetOffset || new THREE.Vector3(0, 0, 0),
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
        targetOffset: snapshot.targetOffset,
        offset,
      });
      renderDirectionalLightsList();
      if (onStructureChange) onStructureChange();
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
        const targetOffset = light.userData?.targetOffset || new THREE.Vector3(0, 0, 0);
        return {
          type: light.isSpotLight ? 'spot' : 'directional',
          color: toHexColor(light.color),
          intensity: light.intensity,
          offset: { x: offset.x, y: offset.y, z: offset.z },
          targetOffset: { x: targetOffset.x, y: targetOffset.y, z: targetOffset.z },
          distance: light.isSpotLight ? light.distance : undefined,
          angle: light.isSpotLight ? light.angle : undefined,
          penumbra: light.isSpotLight ? light.penumbra : undefined,
          decay: light.isSpotLight ? light.decay : undefined,
        };
      }),
    };
  }

  function normalizeLightState(state) {
    const fallback = {
      ambient: { color: '#ffffff', intensity: 1.0 },
      directional: [],
    };
    if (!state || typeof state !== 'object') return fallback;
    const ambient = state.ambient || fallback.ambient;
    const directional = Array.isArray(state.directional) ? state.directional : [];
    return {
      ambient: {
        color: ambient.color || '#ffffff',
        intensity: Number.isFinite(ambient.intensity) ? ambient.intensity : 1.0,
      },
      directional: directional.map((light) => ({
        type: light?.type || 'directional',
        color: light?.color || '#ffffff',
        intensity: Number.isFinite(light?.intensity) ? light.intensity : 1.0,
        offset: light?.offset || { x: 10, y: 10, z: 10 },
        targetOffset: light?.targetOffset || { x: 0, y: 0, z: 0 },
        distance: Number.isFinite(light?.distance) ? light.distance : undefined,
        angle: Number.isFinite(light?.angle) ? light.angle : undefined,
        penumbra: Number.isFinite(light?.penumbra) ? light.penumbra : undefined,
        decay: Number.isFinite(light?.decay) ? light.decay : undefined,
      })),
    };
  }

  function lerpHue(a, b, t) {
    let delta = b - a;
    if (delta > 0.5) delta -= 1;
    if (delta < -0.5) delta += 1;
    let next = a + delta * t;
    if (next < 0) next += 1;
    if (next > 1) next -= 1;
    return next;
  }

  function lerpColorHSL(startColor, endColor, t) {
    const startHsl = { h: 0, s: 0, l: 0 };
    const endHsl = { h: 0, s: 0, l: 0 };
    startColor.getHSL(startHsl);
    endColor.getHSL(endHsl);
    const h = lerpHue(startHsl.h, endHsl.h, t);
    const s = startHsl.s + (endHsl.s - startHsl.s) * t;
    const l = startHsl.l + (endHsl.l - startHsl.l) * t;
    return new THREE.Color().setHSL(h, s, l);
  }

  function ensureDirectionalLightAt(index, type) {
    const current = directionalLights[index];
    const needsType = type || 'directional';
    if (current) {
      const currentType = current.isSpotLight ? 'spot' : 'directional';
      if (currentType === needsType) return current;
      removeDirectionalLight(index);
    }
    const light = needsType === 'spot'
      ? new THREE.SpotLight(0xffffff, 1.0)
      : new THREE.DirectionalLight(0xffffff, 1.0);
    const helper = createDirectionalHelper(light);
    directionalLights.splice(index, 0, light);
    directionalHelpers.splice(index, 0, helper);
    world.add(light);
    world.add(light.target);
    return light;
  }

  function removeTransitionExtra(index) {
    const entry = transitionExtras.get(index);
    if (!entry) return;
    if (entry.helper) {
      scene.remove(entry.helper);
      if (entry.helper.dispose) entry.helper.dispose();
    }
    if (entry.light) {
      if (entry.light.target) world.remove(entry.light.target);
      world.remove(entry.light);
    }
    transitionExtras.delete(index);
  }

  function ensureTransitionExtra(index, type) {
    const existing = transitionExtras.get(index);
    const needsType = type || 'directional';
    if (existing) {
      const existingType = existing.light?.isSpotLight ? 'spot' : 'directional';
      if (existingType === needsType) return existing;
      removeTransitionExtra(index);
    }
    const light = needsType === 'spot'
      ? new THREE.SpotLight(0xffffff, 1.0)
      : new THREE.DirectionalLight(0xffffff, 1.0);
    const helper = createDirectionalHelper(light);
    world.add(light);
    world.add(light.target);
    scene.add(helper);
    const entry = { light, helper };
    transitionExtras.set(index, entry);
    return entry;
  }

  function isLightEntryEqual(a, b) {
    if (!a && !b) return true;
    if (!a || !b) return false;
    const eps = 1e-4;
    const diff = (x, y) => Math.abs(x - y) > eps;
    if ((a.type || 'directional') !== (b.type || 'directional')) return false;
    if ((a.color || '#ffffff') !== (b.color || '#ffffff')) return false;
    if (diff(a.intensity || 0, b.intensity || 0)) return false;
    const ao = a.offset || { x: 0, y: 0, z: 0 };
    const bo = b.offset || { x: 0, y: 0, z: 0 };
    if (diff(ao.x || 0, bo.x || 0) || diff(ao.y || 0, bo.y || 0) || diff(ao.z || 0, bo.z || 0)) return false;
    if (diff(a.distance || 0, b.distance || 0)) return false;
    if (diff(a.angle || 0, b.angle || 0)) return false;
    if (diff(a.penumbra || 0, b.penumbra || 0)) return false;
    if (diff(a.decay || 0, b.decay || 0)) return false;
    const at = a.targetOffset || { x: 0, y: 0, z: 0 };
    const bt = b.targetOffset || { x: 0, y: 0, z: 0 };
    if (diff(at.x || 0, bt.x || 0) || diff(at.y || 0, bt.y || 0) || diff(at.z || 0, bt.z || 0)) return false;
    return true;
  }

  function applyLightEntry(light, entry, intensityScale, modelCenter) {
    if (!light || !entry) return;
    const baseColor = new THREE.Color(entry.color || '#ffffff');
    light.color.copy(baseColor);
    const baseIntensity = Number.isFinite(entry.intensity) ? entry.intensity : 0;
    light.intensity = Math.max(0, baseIntensity * intensityScale);
    const offset = entry.offset || { x: 10, y: 10, z: 10 };
    light.position.copy(modelCenter.clone().add(new THREE.Vector3(offset.x, offset.y, offset.z)));
    const targetOffset = entry.targetOffset || { x: 0, y: 0, z: 0 };
    light.userData.targetOffset = new THREE.Vector3(targetOffset.x || 0, targetOffset.y || 0, targetOffset.z || 0);
    light.target.position.copy(modelCenter.clone().add(light.userData.targetOffset));
    if (light.isSpotLight) {
      if (Number.isFinite(entry.distance)) light.distance = entry.distance;
      if (Number.isFinite(entry.angle)) light.angle = entry.angle;
      if (Number.isFinite(entry.penumbra)) light.penumbra = entry.penumbra;
      if (Number.isFinite(entry.decay)) light.decay = entry.decay;
    }
  }

  function applyLightStateInterpolated(startState, endState, t) {
    const start = normalizeLightState(startState);
    const end = normalizeLightState(endState);
    const modelCenter = getModelCenterModel();

    const hasStartAmbient = !!(startState && typeof startState === 'object' && startState.ambient);
    const hasEndAmbient = !!(endState && typeof endState === 'object' && endState.ambient);

    const startAmbient = new THREE.Color(start.ambient.color || '#ffffff');
    const endAmbient = new THREE.Color(end.ambient.color || '#ffffff');
    if (!hasStartAmbient && hasEndAmbient) {
      ambientLight.color.copy(endAmbient);
      ambientLight.intensity = Math.max(0, (end.ambient.intensity || 0) * t);
    } else if (hasStartAmbient && !hasEndAmbient) {
      ambientLight.color.copy(startAmbient);
      ambientLight.intensity = Math.max(0, (start.ambient.intensity || 0) * (1 - t));
    } else {
      const ambientColor = lerpColorHSL(startAmbient, endAmbient, t);
      const ambientIntensity = (start.ambient.intensity || 0) +
        (end.ambient.intensity - start.ambient.intensity) * t;
      ambientLight.color.copy(ambientColor);
      ambientLight.intensity = Math.max(0, ambientIntensity);
    }

    const maxCount = Math.max(start.directional.length, end.directional.length);
    while (directionalLights.length > maxCount) {
      removeDirectionalLight(directionalLights.length - 1);
    }

    for (let i = 0; i < maxCount; i += 1) {
      const s = start.directional[i] || null;
      const e = end.directional[i] || null;
      if (!s && !e) continue;

      const startEntry = s || e || {};
      const endEntry = e || s || {};
      const type = endEntry.type || startEntry.type || 'directional';
      const light = ensureDirectionalLightAt(i, type);

      const startColor = new THREE.Color(startEntry.color || '#ffffff');
      const endColor = new THREE.Color(endEntry.color || '#ffffff');
      light.color.copy(lerpColorHSL(startColor, endColor, t));

      const startIntensity = Number.isFinite(startEntry.intensity) ? startEntry.intensity : 0;
      const endIntensity = Number.isFinite(endEntry.intensity) ? endEntry.intensity : 0;
      light.intensity = Math.max(0, startIntensity + (endIntensity - startIntensity) * t);

      const startOffset = startEntry.offset || { x: 10, y: 10, z: 10 };
      const endOffset = endEntry.offset || { x: 10, y: 10, z: 10 };
      const offset = new THREE.Vector3(
        (startOffset.x || 0) + ((endOffset.x || 0) - (startOffset.x || 0)) * t,
        (startOffset.y || 0) + ((endOffset.y || 0) - (startOffset.y || 0)) * t,
        (startOffset.z || 0) + ((endOffset.z || 0) - (startOffset.z || 0)) * t
      );
      light.position.copy(modelCenter.clone().add(offset));

      const startTarget = startEntry.targetOffset || { x: 0, y: 0, z: 0 };
      const endTarget = endEntry.targetOffset || { x: 0, y: 0, z: 0 };
      const targetOffset = new THREE.Vector3(
        (startTarget.x || 0) + ((endTarget.x || 0) - (startTarget.x || 0)) * t,
        (startTarget.y || 0) + ((endTarget.y || 0) - (startTarget.y || 0)) * t,
        (startTarget.z || 0) + ((endTarget.z || 0) - (startTarget.z || 0)) * t
      );
      light.userData.targetOffset = targetOffset;
      light.target.position.copy(modelCenter.clone().add(targetOffset));

      if (light.isSpotLight) {
        const startDistance = Number.isFinite(startEntry.distance) ? startEntry.distance : 0;
        const endDistance = Number.isFinite(endEntry.distance) ? endEntry.distance : 0;
        light.distance = startDistance + (endDistance - startDistance) * t;

        const startAngle = Number.isFinite(startEntry.angle) ? startEntry.angle : light.angle;
        const endAngle = Number.isFinite(endEntry.angle) ? endEntry.angle : light.angle;
        light.angle = startAngle + (endAngle - startAngle) * t;

        const startPenumbra = Number.isFinite(startEntry.penumbra) ? startEntry.penumbra : 0;
        const endPenumbra = Number.isFinite(endEntry.penumbra) ? endEntry.penumbra : 0;
        light.penumbra = startPenumbra + (endPenumbra - startPenumbra) * t;

        const startDecay = Number.isFinite(startEntry.decay) ? startEntry.decay : 1;
        const endDecay = Number.isFinite(endEntry.decay) ? endEntry.decay : 1;
        light.decay = startDecay + (endDecay - startDecay) * t;
      }

      const helper = directionalHelpers[i];
      if (helper && light) {
        updateDirectionalHelper(helper, light);
      }

      removeTransitionExtra(i);
      if (!e && t >= 1) {
        removeDirectionalLight(i);
      }
    }
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
      addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10), intensity: 1.5 });
    } else {
      dirList.forEach((item) => {
        const offset = item?.offset || { x: 10, y: 10, z: 10 };
        const targetOffset = item?.targetOffset || { x: 0, y: 0, z: 0 };
        addDirectionalLight({
          type: item?.type || 'directional',
          color: item?.color ? new THREE.Color(item.color) : 0xffffff,
          intensity: Number.isFinite(item?.intensity) ? item.intensity : 1.0,
          offset: new THREE.Vector3(offset.x, offset.y, offset.z),
          position: modelCenter.clone().add(new THREE.Vector3(offset.x, offset.y, offset.z)),
          targetOffset: new THREE.Vector3(targetOffset.x, targetOffset.y, targetOffset.z),
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
    addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10), intensity: 1.5 });
    syncLightInputs();
  }

  function syncLightInputs() {
    if (ambientColorInput) ambientColorInput.value = toHexColor(ambientLight.color);
    if (ambientIntensityInput) ambientIntensityInput.value = ambientLight.intensity.toFixed(3);
    const modelCenter = getModelCenterModel();
    directionalLights.forEach((light, index) => {
      const targetOffset = light.userData?.targetOffset || new THREE.Vector3(0, 0, 0);
      light.target.position.copy(modelCenter.clone().add(targetOffset));
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
        if (!allowStructureEdit) return;
        addDirectionalLight({ offset: new THREE.Vector3(10, 10, 10) });
        renderDirectionalLightsList();
        if (onStructureChange) onStructureChange();
      });
    }

    if (removeDirLightBtn) {
      removeDirLightBtn.addEventListener('click', () => {
        if (!allowStructureEdit) return;
        if (directionalLights.length <= 1) return;
        removeDirectionalLight(activeDirLightIndex);
        renderDirectionalLightsList();
        if (onStructureChange) onStructureChange();
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
    applyLightStateInterpolated,
    applyLightState,
    resetLights,
    setStructureEditable,
    setStructureChangeCallback,
  };
}
