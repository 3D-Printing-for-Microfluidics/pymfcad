import * as THREE from "three";

const UNIT_FACTORS = {
  m: 0.001,
  cm: 0.1,
  mm: 1,
  μm: 1000,
};

const CUSTOM_UNIT_DEFAULTS = {
  xy: 0.0076,
  z: 0.01,
};

function normalizeCustomUnits(value) {
  const xy = Number.parseFloat(value?.xy);
  const z = Number.parseFloat(value?.z);
  return {
    xy: Number.isFinite(xy) && xy > 0 ? xy : CUSTOM_UNIT_DEFAULTS.xy,
    z: Number.isFinite(z) && z > 0 ? z : CUSTOM_UNIT_DEFAULTS.z,
  };
}

export class RulerAxesHelper extends THREE.AxesHelper {
  constructor(size = 1, camera, renderer) {
    super(size);

    this.camera = camera;
    this.renderer = renderer;
    this.size = size;
    this.cameraProvider = null;
    this.controlsProvider = null;
    this.unitsProvider = null;
    this.visibilityProvider = null;
    this.customUnits = { ...CUSTOM_UNIT_DEFAULTS };

    this.majorTickEvery = 5;
    this.targetPixelSpacing = 80;
    this.minorTickLengthFactor = 0.08;
    this.majorTickLengthFactor = 0.28;
    this.labelOffsetFactor = -0.75;
    this.labelScaleFactor = 1.0;

    this._axisChildren = [];
    this._tickChildren = [];
    this._labelChildren = [];
    this.visibilityMode = "all";

    this._axisColors = {
      x: new THREE.Color(0xff5555),
      y: new THREE.Color(0x55ff55),
      z: new THREE.Color(0x5555ff),
    };

    this._tickGroups = {
      x: this._createTickGroup(),
      y: this._createTickGroup(),
      z: this._createTickGroup(),
    };

    this._labelGroups = {
      x: this._createLabelGroup(),
      y: this._createLabelGroup(),
      z: this._createLabelGroup(),
    };

    Object.values(this._tickGroups).forEach((group) => this.add(group));
    Object.values(this._labelGroups).forEach((group) => this.add(group));

    this._lastStep = null;
    this._lastZoom = null;
    this._lastCamera = null;
    this._lastUnits = null;
    this._lastCustomUnitsKey = JSON.stringify(this.customUnits);
    this._axisChildren = this.children.slice(0, 3);

    this.update();
  }

  setCameraProvider(cameraProvider) {
    this.cameraProvider = cameraProvider;
    this.update();
  }

  setControlsProvider(controlsProvider) {
    this.controlsProvider = controlsProvider;
    this.update();
  }

  setUnitsProvider(unitsProvider) {
    this.unitsProvider = unitsProvider;
    this.update();
  }

  setCustomUnits(customUnits) {
    this.customUnits = normalizeCustomUnits(customUnits);
    this.update();
  }

  setVisibilityMode(mode) {
    this.visibilityMode = mode || "all";
    this._applyVisibilityMode();
  }

  update() {
    const camera = this._getCamera();
    if (!camera) return;
    const units = this.unitsProvider ? this.unitsProvider() : "mm";
    const customUnitsKey = JSON.stringify(this.customUnits);

    var step = this._calculateStep(camera);
    if (step === 0) step = 1; // Avoid division by zero

    if (
      step === this._lastStep &&
      camera.zoom === this._lastZoom &&
      camera === this._lastCamera &&
      units === this._lastUnits &&
      customUnitsKey === this._lastCustomUnitsKey
    )
      return;

    this.camera = camera;
    this._lastStep = step;
    this._lastZoom = camera.zoom;
    this._lastCamera = camera;
    this._lastUnits = units;
    this._lastCustomUnitsKey = customUnitsKey;

    const tickStep = Math.max(step, 0.01);
    const majorEvery = Math.max(
      1,
      Math.round((this.majorTickEvery * tickStep) / step),
    );

    this._updateAxisTicks("x", tickStep, majorEvery);
    this._updateAxisTicks("y", tickStep, majorEvery);
    this._updateAxisTicks("z", tickStep, majorEvery);
    this._applyVisibilityMode();
  }

  _getCamera() {
    return this.cameraProvider ? this.cameraProvider() : this.camera;
  }

  _createTickGroup() {
    const minorGeometry = new THREE.BufferGeometry();
    const majorGeometry = new THREE.BufferGeometry();

    const minorMaterial = new THREE.LineBasicMaterial({
      color: 0xffffff,
      toneMapped: false,
    });

    const majorMaterial = new THREE.LineBasicMaterial({
      color: 0xffffff,
      toneMapped: false,
    });

    const group = new THREE.Group();
    group.userData.minorGeometry = minorGeometry;
    group.userData.majorGeometry = majorGeometry;
    group.userData.minorMaterial = minorMaterial;
    group.userData.majorMaterial = majorMaterial;
    group.userData.minorTicks = new THREE.LineSegments(
      minorGeometry,
      minorMaterial,
    );
    group.userData.majorTicks = new THREE.LineSegments(
      majorGeometry,
      majorMaterial,
    );
    this._tickChildren.push(
      group.userData.minorTicks,
      group.userData.majorTicks,
    );
    group.userData.minorTicks.renderOrder = -1000;
    group.userData.majorTicks.renderOrder = -1000;
    minorMaterial.depthTest = true;
    majorMaterial.depthTest = true;
    minorMaterial.depthWrite = false;
    majorMaterial.depthWrite = false;
    group.add(group.userData.minorTicks);
    group.add(group.userData.majorTicks);

    return group;
  }

  _createLabelGroup() {
    const group = new THREE.Group();
    group.renderOrder = -999;
    this._labelChildren.push(group);
    return group;
  }

  _updateAxisTicks(axis, step, majorEvery) {
    const axisGroup = this._tickGroups[axis];
    const labelGroup = this._labelGroups[axis];
    const axisColor = this._axisColors[axis];
    const units = this.unitsProvider ? this.unitsProvider() : "mm";
    const displayFactor =
      units === "custom"
        ? 1 / ((axis === "z" ? this.customUnits.z : this.customUnits.xy) || 1)
        : UNIT_FACTORS[units] || 1;
    const displayStep =
      units === "custom" ? this._niceStep(step * displayFactor) : null;
    const axisStep = units === "custom" ? displayStep / displayFactor : step;
    const minorTickLength = step * this.minorTickLengthFactor;
    const majorTickLength = step * this.majorTickLengthFactor;
    const labelOffset = step * this.labelOffsetFactor;
    const labelScale = step * this.labelScaleFactor;
    const minorPositions = [];
    const majorPositions = [];

    while (labelGroup.children.length > 0) {
      const child = labelGroup.children[labelGroup.children.length - 1];
      labelGroup.remove(child);
      if (child.material?.map) {
        child.material.map.dispose();
      }
      child.material?.dispose?.();
      child.geometry?.dispose?.();
    }

    const minValue = 0;
    const maxValue = this.size;
    const epsilon = axisStep * 0.001;
    const startIndex = Math.ceil(minValue / axisStep);

    for (let index = startIndex; ; index += 1) {
      const value = index * axisStep;
      if (value > maxValue + epsilon) break;

      const isMajor = index % majorEvery === 0;
      const tickLength = isMajor ? majorTickLength : minorTickLength;
      const labelValue =
        units === "custom"
          ? index * displayStep
          : this._roundToStep(value, step) * displayFactor;

      if (axis === "x") {
        (isMajor ? majorPositions : minorPositions).push(
          value,
          -tickLength,
          0,
          value,
          0,
          0,
        );
      } else if (axis === "y") {
        (isMajor ? majorPositions : minorPositions).push(
          -tickLength,
          value,
          0,
          0,
          value,
          0,
        );
      } else {
        (isMajor ? majorPositions : minorPositions).push(
          -tickLength,
          0,
          value,
          0,
          0,
          value,
        );
      }

      if (isMajor) {
        this._addTickLabel(
          labelGroup,
          axis,
          value,
          labelValue,
          axisColor,
          labelOffset,
          labelScale,
        );
      }
    }

    this._setLinePositions(axisGroup.userData.minorGeometry, minorPositions);
    this._setLinePositions(axisGroup.userData.majorGeometry, majorPositions);
    axisGroup.userData.minorMaterial.color.copy(axisColor);
    axisGroup.userData.majorMaterial.color.copy(axisColor);
  }

  _addTickLabel(
    group,
    axis,
    value,
    labelValue,
    color,
    labelOffset,
    labelScale,
  ) {
    const label = this._createLabelTexture(
      String(this._formatTickValue(labelValue)),
      color,
    );
    const material = new THREE.SpriteMaterial({
      map: label,
      transparent: true,
      depthTest: true,
      depthWrite: false,
      toneMapped: false,
    });
    const sprite = new THREE.Sprite(material);
    sprite.renderOrder = -999;
    sprite.scale.set(labelScale, labelScale * 0.5, 1);

    if (axis === "x") {
      sprite.position.set(value, labelOffset, 0);
    } else if (axis === "y") {
      sprite.position.set(labelOffset, value, 0);
    } else {
      sprite.position.set(labelOffset, 0, value);
    }

    group.add(sprite);
  }

  _createLabelTexture(text, color) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "bold 64px Inter, system-ui, -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#000000";
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 8;
    ctx.strokeText(text, canvas.width / 2, canvas.height / 2);
    ctx.fillStyle = `#${color.getHexString()}`;
    ctx.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    texture.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
    return texture;
  }

  _setLinePositions(geometry, positions) {
    geometry.dispose();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );
  }

  _formatTickValue(value) {
    const normalized = Math.abs(value) < 1e-9 ? 0 : value;
    return Number.isInteger(normalized)
      ? normalized
      : Number(normalized.toFixed(2));
  }

  _roundToStep(value, step) {
    return Math.round(value / step) * step;
  }

  _calculateStep(camera = this._getCamera()) {
    if (!camera) return 1;

    let worldPerPixel;

    if (camera.isOrthographicCamera) {
      worldPerPixel =
        (camera.top - camera.bottom) /
        camera.zoom /
        this.renderer.domElement.clientHeight;
    } else {
      const controls = this.controlsProvider ? this.controlsProvider() : null;
      const target = controls?.target || null;
      const distance = target
        ? camera.position.distanceTo(target)
        : camera.position.length();

      const worldHeight =
        2 * distance * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5));

      worldPerPixel = worldHeight / this.renderer.domElement.clientHeight;
    }

    const desired = worldPerPixel * this.targetPixelSpacing;

    return this._niceStep(desired);
  }

  _niceStep(value) {
    const exponent = Math.floor(Math.log10(value));

    const fraction = value / Math.pow(10, exponent);

    let nice;

    if (fraction < 1.5) nice = 1;
    else if (fraction < 3) nice = 2;
    else if (fraction < 7) nice = 5;
    else nice = 10;

    return nice * Math.pow(10, exponent);
  }

  _applyVisibilityMode() {
    const mode = this.visibilityMode || "all";
    const axisVisible = mode === "axis" || mode === "all";
    const tickVisible = mode === "ticks" || mode === "all";
    const labelsVisible = mode === "all";
    this.visible = mode !== "hidden";

    this._axisChildren.forEach((child) => {
      child.visible = this.visible && axisVisible;
    });

    Object.values(this._tickGroups).forEach((group) => {
      group.visible = this.visible && tickVisible;
    });

    Object.values(this._labelGroups).forEach((group) => {
      group.visible = this.visible && labelsVisible;
    });
  }
}
