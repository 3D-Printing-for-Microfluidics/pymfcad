import * as THREE from "three";

export function createLightSystem({
  scene,
  world,
  cameraSystem,
  previewSystem,
  getModelCenterModel,
}) {
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
  world.add(ambientLight);

  const directionalLights = [];
  const directionalHelpers = [];
  const transitionExtras = new Map();
  let defaultLightInitialized = false;
  let lightHelpersVisible = false;
  let activeDirLightIndex = 0;
  const ACTIVE_HELPER_ALPHA = 1.0;
  const INACTIVE_HELPER_ALPHA = 0.33;

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
  let onLightStateChange = null;

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

  function updateDirectionalHelper(helper, light, { isActive = false } = {}) {
    if (helper.setColor) {
      helper.setColor(light.color);
    } else if (helper.material && helper.material.color) {
      helper.material.color.copy(light.color);
    }
    const opacity = isActive ? ACTIVE_HELPER_ALPHA : INACTIVE_HELPER_ALPHA;
    const applyMaterialOpacity = (material) => {
      if (!material) return;
      if (Array.isArray(material)) {
        material.forEach((mat) => applyMaterialOpacity(mat));
        return;
      }
      material.transparent = true;
      material.opacity = opacity;
      material.depthWrite = opacity >= 1;
    };
    if (helper.material) {
      applyMaterialOpacity(helper.material);
    }
    helper.traverse?.((child) => {
      if (child.material) {
        applyMaterialOpacity(child.material);
      }
    });
    helper.update();
  }

  function addDirectionalLight(options = {}) {
    const type = options.type || "directional";
    const light =
      type === "spot"
        ? new THREE.SpotLight(
            options.color ?? 0xffffff,
            options.intensity ?? 1.0,
          )
        : new THREE.DirectionalLight(
            options.color ?? 0xffffff,
            options.intensity ?? 1.0,
          );
    const modelCenter = getModelCenterModel() || new THREE.Vector3(0, 0, 0);
    const defaultPosition = modelCenter
      .clone()
      .add(new THREE.Vector3(10, 10, 10));
    const pos = options.position
      ? options.position.clone
        ? options.position.clone()
        : new THREE.Vector3(
            options.position.x || 0,
            options.position.y || 0,
            options.position.z || 0,
          )
      : defaultPosition;
    const targetPosition = options.targetPosition
      ? options.targetPosition.clone
        ? options.targetPosition.clone()
        : new THREE.Vector3(
            options.targetPosition.x || 0,
            options.targetPosition.y || 0,
            options.targetPosition.z || 0,
          )
      : modelCenter.clone();
    light.position.copy(pos);
    world.add(light);
    world.add(light.target);
    light.userData.targetPosition = targetPosition.clone();
    light.userData.range = Number.isFinite(options.distance)
      ? options.distance
      : Number.isFinite(options.range)
        ? options.range
        : 30;
    light.target.position.copy(light.userData.targetPosition);
    if (light.isSpotLight) {
      if (Number.isFinite(options.distance)) {
        light.distance = options.distance;
      } else if (Number.isFinite(options.range)) {
        light.distance = options.range;
      } else {
        light.distance = light.userData.range;
      }
      if (Number.isFinite(options.angle)) light.angle = options.angle;
      if (Number.isFinite(options.penumbra)) light.penumbra = options.penumbra;
      if (Number.isFinite(options.decay)) light.decay = options.decay;
    }
    const helper = createDirectionalHelper(light);
    directionalLights.push(light);
    directionalHelpers.push(helper);
    activeDirLightIndex = directionalLights.length - 1;
    notifyLightStateChange();
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
    notifyLightStateChange();
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
      ? "Remove Directional Light"
      : "Light structure can only be edited in keyframe 1.";
  }

  function setStructureEditable(isEditable) {
    allowStructureEdit = !!isEditable;
    if (addDirLightBtn) {
      addDirLightBtn.disabled = !allowStructureEdit;
      addDirLightBtn.title = allowStructureEdit
        ? "Add Directional Light"
        : "Light structure can only be edited in keyframe 1.";
    }
    updateRemoveDirLightButton();
    renderDirectionalLightsList();
  }

  function setStructureChangeCallback(callback) {
    onStructureChange = typeof callback === "function" ? callback : null;
  }

  function setLightStateChangeCallback(callback) {
    onLightStateChange = typeof callback === "function" ? callback : null;
  }

  function notifyLightStateChange() {
    if (!onLightStateChange) return;
    onLightStateChange(getLightState());
  }

  function updateDirectionalLightTargets() {
    directionalLights.forEach((light, index) => {
      const targetPosition = light.userData?.targetPosition;
      if (targetPosition && targetPosition.isVector3) {
        light.target.position.copy(targetPosition);
      } else if (targetPosition && Number.isFinite(targetPosition.x)) {
        light.target.position.copy(
          new THREE.Vector3(
            targetPosition.x,
            targetPosition.y,
            targetPosition.z,
          ),
        );
      } else {
        light.userData.targetPosition = light.target.position.clone();
      }
      const helper = directionalHelpers[index];
      if (helper) {
        updateDirectionalHelper(helper, light, {
          isActive: index === activeDirLightIndex,
        });
      }
    });
  }

  function setActiveLightTarget(target) {
    const light = directionalLights[activeDirLightIndex];
    if (!light || !target) return;
    const nextTarget = target.clone
      ? target.clone()
      : new THREE.Vector3(target.x || 0, target.y || 0, target.z || 0);
    const localTarget = nextTarget.clone();
    if (world) {
      world.worldToLocal(localTarget);
    }
    light.userData.targetPosition = localTarget.clone();
    light.target.position.copy(light.userData.targetPosition);
    const helper = directionalHelpers[activeDirLightIndex];
    if (helper) {
      updateDirectionalHelper(helper, light, { isActive: true });
    }
    renderDirectionalLightsList();
    notifyLightStateChange();
  }

  function ensureDefaultLight() {
    if (defaultLightInitialized) return;
    defaultLightInitialized = true;
    addDirectionalLight({ intensity: 1.5 });
  }

  function toHexColor(color) {
    return `#${color.getHexString()}`;
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

  function setDialogOpen(isOpen) {
    if (!dialogEl) return;
    dialogEl.classList.toggle("is-open", isOpen);
    if (previewSystem) {
      previewSystem.setOpen(isOpen);
    }
  }

  function setHelpersVisible(isVisible) {
    lightHelpersVisible = !!isVisible;
    directionalHelpers.forEach((helper, index) => {
      helper.visible = lightHelpersVisible;
      const light = directionalLights[index];
      if (light) {
        updateDirectionalHelper(helper, light, {
          isActive: index === activeDirLightIndex,
        });
      } else {
        helper.update();
      }
    });
  }

  function renderDirectionalLightsList() {
    if (!directionalLightsList) return;
    directionalLightsList.innerHTML = "";
    if (directionalLights.length === 0) {
      updateRemoveDirLightButton();
      return;
    }

    const buttonsRow = document.createElement("div");
    buttonsRow.className = "light-list";
    directionalLights.forEach((_, index) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "light-btn";
      btn.textContent = String(index + 1);
      if (index === activeDirLightIndex) {
        btn.classList.add("is-active");
      }
      btn.addEventListener("click", () => {
        activeDirLightIndex = index;
        renderDirectionalLightsList();
        updateDirectionalLightTargets();
      });
      buttonsRow.appendChild(btn);
    });
    directionalLightsList.appendChild(buttonsRow);

    updateRemoveDirLightButton();
    updateDirectionalLightTargets();

    const light = directionalLights[activeDirLightIndex];
    if (!light) return;
    const modelCenter = getModelCenterModel();

    const editor = document.createElement("div");
    editor.className = "dir-light-row";

    const gridPrimary = document.createElement("div");
    gridPrimary.className = "input-grid";

    const colorLabel = document.createElement("label");
    colorLabel.textContent = "Color";
    const colorInput = document.createElement("input");
    colorInput.type = "color";
    colorInput.value = toHexColor(light.color);
    colorLabel.appendChild(colorInput);
    gridPrimary.appendChild(colorLabel);

    const intensityLabel = document.createElement("label");
    intensityLabel.textContent = "Intensity";
    const intensityInput = document.createElement("input");
    intensityInput.type = "text";
    intensityInput.inputMode = "decimal";
    intensityInput.step = "0.1";
    intensityInput.min = "0";
    intensityInput.value = light.intensity.toFixed(3);
    intensityLabel.appendChild(intensityInput);
    gridPrimary.appendChild(intensityLabel);

    const typeLabel = document.createElement("label");
    typeLabel.textContent = "Type";
    const typeSelect = document.createElement("select");
    typeSelect.innerHTML =
      '<option value="directional">Directional</option><option value="spot">Spot</option>';
    typeSelect.value = light.isSpotLight ? "spot" : "directional";
    typeSelect.disabled = !allowStructureEdit;
    if (!allowStructureEdit) {
      typeSelect.title = "Light type can only be changed in keyframe 1.";
    }
    typeLabel.appendChild(typeSelect);
    gridPrimary.appendChild(typeLabel);

    const gridPosition = document.createElement("div");
    gridPosition.className = "input-grid";

    const targetWorld =
      light.userData?.targetPosition && light.userData.targetPosition.isVector3
        ? light.userData.targetPosition.clone()
        : light.userData?.targetPosition &&
            Number.isFinite(light.userData.targetPosition.x)
          ? new THREE.Vector3(
              light.userData.targetPosition.x,
              light.userData.targetPosition.y,
              light.userData.targetPosition.z,
            )
          : light.target.position.clone();
    light.userData.targetPosition = targetWorld.clone();
    const direction = light.position.clone().sub(targetWorld);
    const { yaw, pitch } = directionToAngles(direction);
    const distanceValue = direction.length();

    const targetXLabel = document.createElement("label");
    targetXLabel.textContent = "Target X";
    const targetXInput = document.createElement("input");
    targetXInput.type = "text";
    targetXInput.inputMode = "decimal";
    targetXInput.step = "0.1";
    targetXInput.value = targetWorld.x.toFixed(3);
    targetXLabel.appendChild(targetXInput);
    gridPosition.appendChild(targetXLabel);

    const targetYLabel = document.createElement("label");
    targetYLabel.textContent = "Target Y";
    const targetYInput = document.createElement("input");
    targetYInput.type = "text";
    targetYInput.inputMode = "decimal";
    targetYInput.step = "0.1";
    targetYInput.value = targetWorld.y.toFixed(3);
    targetYLabel.appendChild(targetYInput);
    gridPosition.appendChild(targetYLabel);

    const targetZLabel = document.createElement("label");
    targetZLabel.textContent = "Target Z";
    const targetZInput = document.createElement("input");
    targetZInput.type = "text";
    targetZInput.inputMode = "decimal";
    targetZInput.step = "0.1";
    targetZInput.value = targetWorld.z.toFixed(3);
    targetZLabel.appendChild(targetZInput);
    gridPosition.appendChild(targetZLabel);

    const distanceLabel = document.createElement("label");
    distanceLabel.textContent = "Distance";
    const distanceInput = document.createElement("input");
    distanceInput.type = "text";
    distanceInput.inputMode = "decimal";
    distanceInput.step = "0.1";
    distanceInput.min = "0";
    distanceInput.value = distanceValue.toFixed(3);
    distanceLabel.appendChild(distanceInput);
    gridPosition.appendChild(distanceLabel);

    const yawLabel = document.createElement("label");
    yawLabel.textContent = "Yaw (deg)";
    const yawInput = document.createElement("input");
    yawInput.type = "text";
    yawInput.inputMode = "decimal";
    yawInput.step = "1";
    yawInput.value = yaw.toFixed(2);
    yawLabel.appendChild(yawInput);
    gridPosition.appendChild(yawLabel);

    const pitchLabel = document.createElement("label");
    pitchLabel.textContent = "Pitch (deg)";
    const pitchInput = document.createElement("input");
    pitchInput.type = "text";
    pitchInput.inputMode = "decimal";
    pitchInput.step = "1";
    pitchInput.min = "-89.9999";
    pitchInput.max = "89.9999";
    pitchInput.value = pitch.toFixed(2);
    pitchLabel.appendChild(pitchInput);
    gridPosition.appendChild(pitchLabel);

    editor.appendChild(gridPrimary);
    editor.appendChild(gridPosition);

    const spotSection = document.createElement("div");
    spotSection.style.marginTop = "0.75rem";

    const spotDivider = document.createElement("hr");
    spotDivider.style.border = "none";
    spotDivider.style.borderTop =
      "1px solid var(--panel-border, rgba(255,255,255,0.12))";
    spotDivider.style.margin = "0.25rem 0 0.75rem";
    spotSection.appendChild(spotDivider);

    const spotHeader = document.createElement("div");
    spotHeader.className = "section-header";
    const spotTitle = document.createElement("h5");
    spotTitle.textContent = "Spotlight Settings";
    spotTitle.style.margin = "0";
    spotHeader.appendChild(spotTitle);
    spotSection.appendChild(spotHeader);

    const gridSpot = document.createElement("div");
    gridSpot.className = "input-grid";
    spotSection.appendChild(gridSpot);

    const rangeLabel = document.createElement("label");
    rangeLabel.textContent = "Spot Range";
    const rangeInput = document.createElement("input");
    rangeInput.type = "text";
    rangeInput.inputMode = "decimal";
    rangeInput.step = "0.1";
    rangeInput.min = "0";
    const storedRange = Number.isFinite(light.userData?.range)
      ? light.userData.range
      : light.isSpotLight
        ? light.distance
        : 30;
    rangeInput.value = storedRange.toFixed(3);
    rangeLabel.appendChild(rangeInput);
    gridSpot.appendChild(rangeLabel);

    const decayLabel = document.createElement("label");
    decayLabel.textContent = "Decay";
    const decayInput = document.createElement("input");
    decayInput.type = "text";
    decayInput.inputMode = "decimal";
    decayInput.step = "0.1";
    decayInput.min = "0";
    decayInput.value = light.isSpotLight ? light.decay.toFixed(2) : "1";
    decayLabel.appendChild(decayInput);
    gridSpot.appendChild(decayLabel);

    const angleLabel = document.createElement("label");
    angleLabel.textContent = "Cone Angle (deg)";
    const angleInput = document.createElement("input");
    angleInput.type = "text";
    angleInput.inputMode = "decimal";
    angleInput.step = "1";
    angleInput.min = "1";
    angleInput.max = "90";
    angleInput.value = light.isSpotLight
      ? THREE.MathUtils.radToDeg(light.angle).toFixed(1)
      : "30";
    angleLabel.appendChild(angleInput);
    gridSpot.appendChild(angleLabel);

    const penumbraLabel = document.createElement("label");
    penumbraLabel.textContent = "Penumbra";
    const penumbraInput = document.createElement("input");
    penumbraInput.type = "text";
    penumbraInput.inputMode = "decimal";
    penumbraInput.step = "0.01";
    penumbraInput.min = "0";
    penumbraInput.max = "1";
    penumbraInput.value = light.isSpotLight ? light.penumbra.toFixed(2) : "0";
    penumbraLabel.appendChild(penumbraInput);
    gridSpot.appendChild(penumbraLabel);

    editor.appendChild(spotSection);

    const syncSpotVisibility = () => {
      spotSection.style.display = light.isSpotLight ? "" : "none";
    };
    syncSpotVisibility();

    function updateLight() {
      const currentTarget =
        light.userData?.targetPosition &&
        light.userData.targetPosition.isVector3
          ? light.userData.targetPosition.clone()
          : targetWorld.clone();
      const currentDir = light.position.clone().sub(currentTarget);
      const { yaw: currentYaw, pitch: currentPitch } =
        directionToAngles(currentDir);
      const currentDistance = currentDir.length();

      const nextIntensity = evaluateNumericInput(
        intensityInput.value,
        light.intensity,
      );
      const yawDeg = evaluateNumericInput(yawInput.value, currentYaw);
      const pitchDeg = evaluateNumericInput(pitchInput.value, currentPitch);
      const distanceVal = evaluateNumericInput(
        distanceInput.value,
        currentDistance,
      );
      if (Number.isFinite(nextIntensity)) {
        light.intensity = Math.max(0, nextIntensity);
      }
      light.color.set(colorInput.value);
      const tX = evaluateNumericInput(targetXInput.value, currentTarget.x);
      const tY = evaluateNumericInput(targetYInput.value, currentTarget.y);
      const tZ = evaluateNumericInput(targetZInput.value, currentTarget.z);
      const nextTarget = new THREE.Vector3(
        Number.isFinite(tX) ? tX : currentTarget.x,
        Number.isFinite(tY) ? tY : currentTarget.y,
        Number.isFinite(tZ) ? tZ : currentTarget.z,
      );
      light.userData.targetPosition = nextTarget.clone();
      light.target.position.copy(nextTarget);
      if (
        Number.isFinite(yawDeg) &&
        Number.isFinite(pitchDeg) &&
        Number.isFinite(distanceVal)
      ) {
        const direction = anglesToDirection(yawDeg, pitchDeg);
        light.position.copy(
          nextTarget
            .clone()
            .add(direction.multiplyScalar(Math.max(0, distanceVal))),
        );
      }
      if (light.isSpotLight) {
        const dist = evaluateNumericInput(
          rangeInput.value,
          light.userData?.range ?? light.distance ?? 0,
        );
        const angleDeg = evaluateNumericInput(
          angleInput.value,
          THREE.MathUtils.radToDeg(light.angle),
        );
        const pen = evaluateNumericInput(penumbraInput.value, light.penumbra);
        const decay = evaluateNumericInput(decayInput.value, light.decay);
        if (Number.isFinite(dist)) {
          light.userData.range = Math.max(0, dist);
          light.distance = light.userData.range;
        }
        if (Number.isFinite(angleDeg)) {
          const angleRad = THREE.MathUtils.degToRad(
            Math.min(90, Math.max(1, angleDeg)),
          );
          light.angle = angleRad;
        }
        if (Number.isFinite(pen))
          light.penumbra = Math.min(1, Math.max(0, pen));
        if (Number.isFinite(decay)) light.decay = Math.max(0, decay);
      } else {
        const dist = evaluateNumericInput(
          rangeInput.value,
          light.userData?.range ?? 0,
        );
        if (Number.isFinite(dist)) {
          light.userData.range = Math.max(0, dist);
        }
      }
      const helper = directionalHelpers[activeDirLightIndex];
      if (helper) {
        updateDirectionalHelper(helper, light, { isActive: true });
      }
      notifyLightStateChange();
      syncEditorInputsFromState();
    }

    function syncEditorInputsFromState() {
      const liveTarget =
        light.userData?.targetPosition &&
        light.userData.targetPosition.isVector3
          ? light.userData.targetPosition.clone()
          : light.target.position.clone();
      const liveDir = light.position.clone().sub(liveTarget);
      const { yaw: liveYaw, pitch: livePitch } = directionToAngles(liveDir);
      const liveDistance = liveDir.length();

      intensityInput.value = light.intensity.toFixed(3);
      targetXInput.value = liveTarget.x.toFixed(3);
      targetYInput.value = liveTarget.y.toFixed(3);
      targetZInput.value = liveTarget.z.toFixed(3);
      distanceInput.value = liveDistance.toFixed(3);
      yawInput.value = liveYaw.toFixed(2);
      pitchInput.value = livePitch.toFixed(2);

      if (light.isSpotLight) {
        const rangeValue = Number.isFinite(light.userData?.range)
          ? light.userData.range
          : light.distance;
        rangeInput.value = Number.isFinite(rangeValue)
          ? rangeValue.toFixed(3)
          : "0";
        decayInput.value = light.decay.toFixed(2);
        angleInput.value = THREE.MathUtils.radToDeg(light.angle).toFixed(1);
        penumbraInput.value = light.penumbra.toFixed(2);
      } else {
        const rangeValue = Number.isFinite(light.userData?.range)
          ? light.userData.range
          : 0;
        rangeInput.value = rangeValue.toFixed(3);
      }
    }

    const commitOnEnter = (handler) => (event) => {
      if (event.key === "Enter") {
        handler();
      }
    };

    const commitInputs = [
      colorInput,
      intensityInput,
      yawInput,
      pitchInput,
      distanceInput,
      angleInput,
      penumbraInput,
      decayInput,
      rangeInput,
      targetXInput,
      targetYInput,
      targetZInput,
    ].filter(Boolean);

    commitInputs.forEach((input) => {
      input.addEventListener("change", updateLight);
      input.addEventListener("keydown", commitOnEnter(updateLight));
    });

    typeSelect.addEventListener("change", () => {
      const nextType = typeSelect.value;
      const current = directionalLights[activeDirLightIndex];
      if (!current) return;
      const rangeValue = Number.isFinite(parseFloat(rangeInput.value))
        ? parseFloat(rangeInput.value)
        : Number.isFinite(current.userData?.range)
          ? current.userData.range
          : 30;
      const snapshot = {
        color: current.color.getHex(),
        intensity: current.intensity,
        distance: current.isSpotLight ? current.distance : rangeValue,
        angle: current.isSpotLight
          ? current.angle
          : THREE.MathUtils.degToRad(parseFloat(angleInput.value)),
        penumbra: current.isSpotLight
          ? current.penumbra
          : parseFloat(penumbraInput.value),
        decay: current.isSpotLight
          ? current.decay
          : parseFloat(decayInput.value),
        targetPosition:
          current.userData?.targetPosition &&
          current.userData.targetPosition.isVector3
            ? current.userData.targetPosition.clone()
            : current.target.position.clone(),
        position: current.position.clone(),
        range: rangeValue,
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
        targetPosition: snapshot.targetPosition,
        position: snapshot.position,
        range: snapshot.range,
      });
      renderDirectionalLightsList();
      if (onStructureChange) onStructureChange();
    });
    directionalLightsList.appendChild(editor);
  }

  function getLightState() {
    return {
      ambient: {
        color: toHexColor(ambientLight.color),
        intensity: ambientLight.intensity,
      },
      directional: directionalLights.map((light) => {
        const targetPosition =
          light.userData?.targetPosition &&
          light.userData.targetPosition.isVector3
            ? light.userData.targetPosition.clone()
            : light.target.position.clone();
        return {
          type: light.isSpotLight ? "spot" : "directional",
          color: toHexColor(light.color),
          intensity: light.intensity,
          position: {
            x: light.position.x,
            y: light.position.y,
            z: light.position.z,
          },
          targetPosition: {
            x: targetPosition.x,
            y: targetPosition.y,
            z: targetPosition.z,
          },
          distance: light.isSpotLight ? light.distance : undefined,
          range: Number.isFinite(light.userData?.range)
            ? light.userData.range
            : undefined,
          angle: light.isSpotLight ? light.angle : undefined,
          penumbra: light.isSpotLight ? light.penumbra : undefined,
          decay: light.isSpotLight ? light.decay : undefined,
        };
      }),
    };
  }

  function normalizeLightState(state) {
    const fallback = {
      ambient: { color: "#ffffff", intensity: 1.0 },
      directional: [],
    };
    if (!state || typeof state !== "object") return fallback;
    const ambient = state.ambient || fallback.ambient;
    const directional = Array.isArray(state.directional)
      ? state.directional
      : [];
    return {
      ambient: {
        color: ambient.color || "#ffffff",
        intensity: Number.isFinite(ambient.intensity) ? ambient.intensity : 1.0,
      },
      directional: directional.map((light) => ({
        type: light?.type || "directional",
        color: light?.color || "#ffffff",
        intensity: Number.isFinite(light?.intensity) ? light.intensity : 1.0,
        position: light?.position,
        targetPosition: light?.targetPosition,
        distance: Number.isFinite(light?.distance) ? light.distance : undefined,
        range: Number.isFinite(light?.range) ? light.range : undefined,
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
    const needsType = type || "directional";
    if (current) {
      const currentType = current.isSpotLight ? "spot" : "directional";
      if (currentType === needsType) return current;
      removeDirectionalLight(index);
    }
    const light =
      needsType === "spot"
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
    const needsType = type || "directional";
    if (existing) {
      const existingType = existing.light?.isSpotLight ? "spot" : "directional";
      if (existingType === needsType) return existing;
      removeTransitionExtra(index);
    }
    const light =
      needsType === "spot"
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
    const getPos = (entry) => entry.position || null;
    const getTarget = (entry) => entry.targetPosition || null;
    if ((a.type || "directional") !== (b.type || "directional")) return false;
    if ((a.color || "#ffffff") !== (b.color || "#ffffff")) return false;
    if (diff(a.intensity || 0, b.intensity || 0)) return false;
    const ap = getPos(a);
    const bp = getPos(b);
    if (ap || bp) {
      if (!ap || !bp) return false;
      if (
        diff(ap.x || 0, bp.x || 0) ||
        diff(ap.y || 0, bp.y || 0) ||
        diff(ap.z || 0, bp.z || 0)
      )
        return false;
    }
    if (diff(a.distance || 0, b.distance || 0)) return false;
    if (diff(a.range || 0, b.range || 0)) return false;
    if (diff(a.angle || 0, b.angle || 0)) return false;
    if (diff(a.penumbra || 0, b.penumbra || 0)) return false;
    if (diff(a.decay || 0, b.decay || 0)) return false;
    const at = getTarget(a);
    const bt = getTarget(b);
    if (at || bt) {
      if (!at || !bt) return false;
      if (
        diff(at.x || 0, bt.x || 0) ||
        diff(at.y || 0, bt.y || 0) ||
        diff(at.z || 0, bt.z || 0)
      )
        return false;
    }
    return true;
  }

  function applyLightEntry(light, entry, intensityScale, modelCenter) {
    if (!light || !entry) return;
    const baseColor = new THREE.Color(entry.color || "#ffffff");
    light.color.copy(baseColor);
    const baseIntensity = Number.isFinite(entry.intensity)
      ? entry.intensity
      : 0;
    light.intensity = Math.max(0, baseIntensity * intensityScale);
    if (entry.position && Number.isFinite(entry.position.x)) {
      light.position.copy(
        new THREE.Vector3(entry.position.x, entry.position.y, entry.position.z),
      );
    } else {
      light.position.copy(
        modelCenter.clone().add(new THREE.Vector3(10, 10, 10)),
      );
    }
    if (entry.targetPosition && Number.isFinite(entry.targetPosition.x)) {
      light.userData.targetPosition = new THREE.Vector3(
        entry.targetPosition.x,
        entry.targetPosition.y,
        entry.targetPosition.z,
      );
    } else {
      light.userData.targetPosition = modelCenter.clone();
    }
    light.target.position.copy(light.userData.targetPosition);
    if (light.isSpotLight) {
      if (Number.isFinite(entry.distance)) light.distance = entry.distance;
      if (Number.isFinite(entry.angle)) light.angle = entry.angle;
      if (Number.isFinite(entry.penumbra)) light.penumbra = entry.penumbra;
      if (Number.isFinite(entry.decay)) light.decay = entry.decay;
    }
    if (Number.isFinite(entry.range)) {
      light.userData.range = entry.range;
      if (light.isSpotLight && !Number.isFinite(entry.distance)) {
        light.distance = entry.range;
      }
    }
  }

  function applyLightStateInterpolated(startState, endState, t) {
    const start = normalizeLightState(startState);
    const end = normalizeLightState(endState);
    const modelCenter = getModelCenterModel();

    const hasStartAmbient = !!(
      startState &&
      typeof startState === "object" &&
      startState.ambient
    );
    const hasEndAmbient = !!(
      endState &&
      typeof endState === "object" &&
      endState.ambient
    );

    const startAmbient = new THREE.Color(start.ambient.color || "#ffffff");
    const endAmbient = new THREE.Color(end.ambient.color || "#ffffff");
    if (!hasStartAmbient && hasEndAmbient) {
      ambientLight.color.copy(endAmbient);
      ambientLight.intensity = Math.max(0, (end.ambient.intensity || 0) * t);
    } else if (hasStartAmbient && !hasEndAmbient) {
      ambientLight.color.copy(startAmbient);
      ambientLight.intensity = Math.max(
        0,
        (start.ambient.intensity || 0) * (1 - t),
      );
    } else {
      const ambientColor = lerpColorHSL(startAmbient, endAmbient, t);
      const ambientIntensity =
        (start.ambient.intensity || 0) +
        (end.ambient.intensity - start.ambient.intensity) * t;
      ambientLight.color.copy(ambientColor);
      ambientLight.intensity = Math.max(0, ambientIntensity);
    }

    const maxCount = Math.max(start.directional.length, end.directional.length);
    while (directionalLights.length > maxCount) {
      removeDirectionalLight(directionalLights.length - 1);
    }

    const defaultPos = modelCenter.clone().add(new THREE.Vector3(10, 10, 10));
    for (let i = 0; i < maxCount; i += 1) {
      const s = start.directional[i] || null;
      const e = end.directional[i] || null;
      if (!s && !e) continue;

      const startEntry = s || e || {};
      const endEntry = e || s || {};
      const type = endEntry.type || startEntry.type || "directional";
      const light = ensureDirectionalLightAt(i, type);

      const startColor = new THREE.Color(startEntry.color || "#ffffff");
      const endColor = new THREE.Color(endEntry.color || "#ffffff");
      light.color.copy(lerpColorHSL(startColor, endColor, t));

      const startIntensity = Number.isFinite(startEntry.intensity)
        ? startEntry.intensity
        : 0;
      const endIntensity = Number.isFinite(endEntry.intensity)
        ? endEntry.intensity
        : 0;
      light.intensity = Math.max(
        0,
        startIntensity + (endIntensity - startIntensity) * t,
      );

      const startPos =
        startEntry.position && Number.isFinite(startEntry.position.x)
          ? startEntry.position
          : { x: defaultPos.x, y: defaultPos.y, z: defaultPos.z };
      const endPos =
        endEntry.position && Number.isFinite(endEntry.position.x)
          ? endEntry.position
          : { x: defaultPos.x, y: defaultPos.y, z: defaultPos.z };
      light.position.set(
        (startPos.x || 0) + ((endPos.x || 0) - (startPos.x || 0)) * t,
        (startPos.y || 0) + ((endPos.y || 0) - (startPos.y || 0)) * t,
        (startPos.z || 0) + ((endPos.z || 0) - (startPos.z || 0)) * t,
      );

      const startTarget =
        startEntry.targetPosition &&
        Number.isFinite(startEntry.targetPosition.x)
          ? startEntry.targetPosition
          : { x: modelCenter.x, y: modelCenter.y, z: modelCenter.z };
      const endTarget =
        endEntry.targetPosition && Number.isFinite(endEntry.targetPosition.x)
          ? endEntry.targetPosition
          : { x: modelCenter.x, y: modelCenter.y, z: modelCenter.z };
      light.userData.targetPosition = new THREE.Vector3(
        (startTarget.x || 0) + ((endTarget.x || 0) - (startTarget.x || 0)) * t,
        (startTarget.y || 0) + ((endTarget.y || 0) - (startTarget.y || 0)) * t,
        (startTarget.z || 0) + ((endTarget.z || 0) - (startTarget.z || 0)) * t,
      );
      light.target.position.copy(light.userData.targetPosition);

      if (light.isSpotLight) {
        const startDistance = Number.isFinite(startEntry.distance)
          ? startEntry.distance
          : 0;
        const endDistance = Number.isFinite(endEntry.distance)
          ? endEntry.distance
          : 0;
        light.distance = startDistance + (endDistance - startDistance) * t;

        const startAngle = Number.isFinite(startEntry.angle)
          ? startEntry.angle
          : light.angle;
        const endAngle = Number.isFinite(endEntry.angle)
          ? endEntry.angle
          : light.angle;
        light.angle = startAngle + (endAngle - startAngle) * t;

        const startPenumbra = Number.isFinite(startEntry.penumbra)
          ? startEntry.penumbra
          : 0;
        const endPenumbra = Number.isFinite(endEntry.penumbra)
          ? endEntry.penumbra
          : 0;
        light.penumbra = startPenumbra + (endPenumbra - startPenumbra) * t;

        const startDecay = Number.isFinite(startEntry.decay)
          ? startEntry.decay
          : 1;
        const endDecay = Number.isFinite(endEntry.decay) ? endEntry.decay : 1;
        light.decay = startDecay + (endDecay - startDecay) * t;
      }

      if (
        Number.isFinite(startEntry.range) ||
        Number.isFinite(endEntry.range)
      ) {
        const startRange = Number.isFinite(startEntry.range)
          ? startEntry.range
          : startDistance;
        const endRange = Number.isFinite(endEntry.range)
          ? endEntry.range
          : endDistance;
        light.userData.range = startRange + (endRange - startRange) * t;
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
    if (!state || typeof state !== "object") return;
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
      addDirectionalLight({ intensity: 1.5 });
    } else {
      dirList.forEach((item) => {
        const defaultPosition = modelCenter
          .clone()
          .add(new THREE.Vector3(10, 10, 10));
        const position =
          item?.position && Number.isFinite(item.position.x)
            ? new THREE.Vector3(
                item.position.x,
                item.position.y,
                item.position.z,
              )
            : defaultPosition;
        const targetPosition =
          item?.targetPosition && Number.isFinite(item.targetPosition.x)
            ? new THREE.Vector3(
                item.targetPosition.x,
                item.targetPosition.y,
                item.targetPosition.z,
              )
            : modelCenter.clone();
        addDirectionalLight({
          type: item?.type || "directional",
          color: item?.color ? new THREE.Color(item.color) : 0xffffff,
          intensity: Number.isFinite(item?.intensity) ? item.intensity : 1.0,
          position,
          targetPosition,
          distance: Number.isFinite(item?.distance) ? item.distance : undefined,
          range: Number.isFinite(item?.range) ? item.range : undefined,
          angle: Number.isFinite(item?.angle) ? item.angle : undefined,
          penumbra: Number.isFinite(item?.penumbra) ? item.penumbra : undefined,
          decay: Number.isFinite(item?.decay) ? item.decay : undefined,
        });
      });
    }
    syncLightInputs();
    notifyLightStateChange();
  }

  function resetLights() {
    ambientLight.color.set(0xffffff);
    ambientLight.intensity = 1.0;
    clearDirectionalLights();
    addDirectionalLight({ intensity: 1.5 });
    syncLightInputs();
    notifyLightStateChange();
  }

  function syncLightInputs() {
    if (ambientColorInput)
      ambientColorInput.value = toHexColor(ambientLight.color);
    if (ambientIntensityInput)
      ambientIntensityInput.value = ambientLight.intensity.toFixed(3);
    directionalLights.forEach((light, index) => {
      if (
        light.userData?.targetPosition &&
        light.userData.targetPosition.isVector3
      ) {
        light.target.position.copy(light.userData.targetPosition);
      }
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
      ambientColorInput.addEventListener("input", () => {
        ambientLight.color.set(ambientColorInput.value);
        notifyLightStateChange();
      });
    }

    if (ambientIntensityInput) {
      const commitAmbientIntensity = () => {
        const next = evaluateNumericInput(
          ambientIntensityInput.value,
          ambientLight.intensity,
        );
        if (Number.isFinite(next)) {
          ambientLight.intensity = Math.max(0, next);
          ambientIntensityInput.value = ambientLight.intensity.toFixed(3);
          notifyLightStateChange();
        }
      };
      ambientIntensityInput.addEventListener("change", commitAmbientIntensity);
      ambientIntensityInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          commitAmbientIntensity();
        }
      });
    }

    if (addDirLightBtn) {
      addDirLightBtn.addEventListener("click", () => {
        if (!allowStructureEdit) return;
        addDirectionalLight();
        renderDirectionalLightsList();
        if (onStructureChange) onStructureChange();
        updateDirectionalLightTargets();
      });
    }

    if (removeDirLightBtn) {
      removeDirLightBtn.addEventListener("click", () => {
        if (!allowStructureEdit) return;
        if (directionalLights.length <= 1) return;
        removeDirectionalLight(activeDirLightIndex);
        renderDirectionalLightsList();
        if (onStructureChange) onStructureChange();
        updateDirectionalLightTargets();
      });
    }

    if (openBtn && dialogEl) {
      openBtn.addEventListener("click", () => {
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
      closeBtn.addEventListener("click", () => {
        setDialogOpen(false);
      });
    }

    if (dialogEl) {
      dialogEl.addEventListener("click", (event) => {
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
    setHelpersVisible,
    setActiveLightTarget,
    getLightState,
    applyLightStateInterpolated,
    applyLightState,
    resetLights,
    setStructureEditable,
    setStructureChangeCallback,
    setLightStateChangeCallback,
  };
}
