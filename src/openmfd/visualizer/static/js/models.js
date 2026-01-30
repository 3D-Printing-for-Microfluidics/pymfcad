import * as THREE from '../lib/three/three.module.js';
import { GLTFLoader } from '../lib/three/loaders/GLTFLoader.js';

export function createModelManager({ scene, world }) {
  const loader = new GLTFLoader();
  let glbFiles = [];
  let modelEntries = [];
  let modelGroups = [];
  let modelVersionScenes = [];
  let models = [];
  let lastModifieds = [];
  let listSignature = '';
  let visibilityResolver = null;
  const visibilityOverrides = new Map();
  let defaultVersionStrategy = 'largest';

  function setVisibilityResolver(resolver) {
    visibilityResolver = resolver;
  }

  function getVisibility(idx) {
    if (visibilityOverrides.has(idx)) return visibilityOverrides.get(idx);
    if (!visibilityResolver) return true;
    return visibilityResolver(idx);
  }

  function setVisibilityOverride(idx, visible) {
    if (!Number.isInteger(idx)) return;
    visibilityOverrides.set(idx, !!visible);
    updateVisibility();
  }

  function setVisibilityOverrides(map) {
    visibilityOverrides.clear();
    if (map) {
      if (map instanceof Map) {
        map.forEach((value, key) => {
          if (Number.isInteger(key)) visibilityOverrides.set(key, !!value);
        });
      } else {
        Object.entries(map).forEach(([key, value]) => {
          const idx = Number.parseInt(key, 10);
          if (Number.isInteger(idx)) visibilityOverrides.set(idx, !!value);
        });
      }
    }
    updateVisibility();
  }

  function clearVisibilityOverrides() {
    visibilityOverrides.clear();
    updateVisibility();
  }

  async function fetchModelList() {
    try {
      const resp = await fetch('/glb_list.json', { cache: 'no-store' });
      const list = await resp.json();
      return list;
    } catch (e) {
      return null;
    }
  }

  function computeSignature(list) {
    return JSON.stringify(list || []);
  }

  function getListSignature() {
    return listSignature;
  }

  function setModelList(list) {
    glbFiles = Array.isArray(list) ? list : [];
    listSignature = computeSignature(glbFiles);
    lastModifieds = Array(glbFiles.length).fill(null);
    modelEntries = buildModelEntries(glbFiles);
  }

  function getModelList() {
    return modelEntries;
  }

  function setDefaultVersionStrategy(strategy) {
    defaultVersionStrategy = strategy === 'smallest' ? 'smallest' : 'largest';
  }

  function applyDefaultVersionStrategy() {
    modelEntries.forEach((entry) => {
      if (!entry.versions.length) return;
      if (defaultVersionStrategy === 'smallest') {
        entry.versionId = entry.versions[0].id;
      } else {
        entry.versionId = entry.versions[entry.versions.length - 1].id;
      }
    });
  }

  function getVersionSelections() {
    const map = {};
    modelEntries.forEach((entry, idx) => {
      map[`glb_ver_${idx}`] = entry.versionId;
    });
    return map;
  }

  function parseVersionedName(rawName = '') {
    const match = /^(.*)__v(\d+)$/i.exec(rawName);
    if (!match) return { base: rawName, version: null };
    return { base: match[1], version: `v${match[2]}` };
  }

  function buildModelEntries(list) {
    const entriesByKey = new Map();
    (list || []).forEach((glb) => {
      const rawBase = glb.base_name || glb.baseName || glb.base || glb.name || '';
      const parsed = parseVersionedName(rawBase || glb.name || '');
      const baseKey = parsed.base || rawBase || glb.name || glb.file || '';
      const versionId = glb.version || parsed.version || 'v0';
      const displayName = glb.name || parsed.base || baseKey;
      const type = (glb.type || 'unknown').toLowerCase();

      if (!entriesByKey.has(baseKey)) {
        entriesByKey.set(baseKey, {
          id: baseKey,
          name: displayName,
          type,
          versions: [],
          versionId: null,
        });
      }

      const entry = entriesByKey.get(baseKey);
      entry.versions.push({
        id: versionId,
        label: versionId === 'v0' ? 'V0' : versionId.toUpperCase(),
        file: glb.file,
      });
    });

    const entries = Array.from(entriesByKey.values());
    entries.forEach((entry) => {
      entry.versions.sort((a, b) => {
        if (a.id === 'v0') return -1;
        if (b.id === 'v0') return 1;
        const aMatch = /^v(\d+)$/i.exec(a.id);
        const bMatch = /^v(\d+)$/i.exec(b.id);
        const aNum = aMatch ? Number.parseInt(aMatch[1], 10) : Number.POSITIVE_INFINITY;
        const bNum = bMatch ? Number.parseInt(bMatch[1], 10) : Number.POSITIVE_INFINITY;
        if (aNum !== bNum) return aNum - bNum;
        return a.id.localeCompare(b.id);
      });
      if (!entry.versionId) {
        entry.versionId = entry.versions[entry.versions.length - 1]?.id || 'v0';
      }
    });
    modelEntries = entries;
    applyDefaultVersionStrategy();
    return entries;
  }

  function disposeGroup(group) {
    if (!group) return;
    if (group.parent === world) world.remove(group);
    group.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((mat) => mat.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  }


  async function loadAllModels() {
    modelGroups.forEach((group) => disposeGroup(group));
    models = [];
    modelGroups = [];
    modelVersionScenes = [];
    lastModifieds = Array(glbFiles.length).fill(null);

    const loadedScenes = await Promise.all(
      modelEntries.map(async (entry, idx) => {
        const versionScenes = new Map();
        const versionLoads = entry.versions.map((ver) =>
          new Promise((resolve) => {
            const cacheBuster = `?cb=${Date.now()}`;
            if (!ver.file) {
              resolve({ id: ver.id, scene: null });
              return;
            }
            loader.load(
              ver.file + cacheBuster,
              (gltf) => resolve({ id: ver.id, scene: gltf.scene }),
              undefined,
              () => resolve({ id: ver.id, scene: null })
            );
          })
        );
        const results = await Promise.all(versionLoads);
        results.forEach(({ id, scene }) => {
          if (!scene) return;
          scene.traverse((child) => {
            if (child.isMesh) {
              const mat = child.material;
              mat.metalness = 0.5;
              mat.transparent = true;
              mat.side = THREE.FrontSide;
              if (Array.isArray(mat)) {
                mat.forEach((m) => {
                  if (m && m.userData && m.userData.baseOpacity === undefined) {
                    m.userData.baseOpacity = Number.isFinite(m.opacity) ? m.opacity : 1;
                  }
                });
              } else if (mat && mat.userData && mat.userData.baseOpacity === undefined) {
                mat.userData.baseOpacity = Number.isFinite(mat.opacity) ? mat.opacity : 1;
              }
            }
          });
          versionScenes.set(id, scene);
        });

        const wrapper = new THREE.Group();
        const activeId = entry.versionId;
        versionScenes.forEach((scene, id) => {
          scene.visible = id === activeId;
          wrapper.add(scene);
        });
        wrapper.visible = getVisibility(idx);
        modelGroups[idx] = wrapper;
        modelVersionScenes[idx] = versionScenes;
        const activeScene = versionScenes.get(activeId) || versionScenes.values().next().value || null;
        models[idx] = activeScene || null;
        world.add(wrapper);
        return wrapper;
      })
    );
    return loadedScenes;
  }

  function setModelVersion(idx, versionId, { reload = true, force = false } = {}) {
    if (!Number.isInteger(idx) || idx < 0 || idx >= modelEntries.length) return;
    const entry = modelEntries[idx];
    if (!entry) return;
    const nextId = versionId || entry.versionId;
    if (entry.versionId === nextId && !force) return;
    entry.versionId = nextId;
    if (!modelGroups[idx]) return;
    const versionMap = modelVersionScenes[idx];
    if (!versionMap) return;
    versionMap.forEach((scene, id) => {
      scene.visible = id === entry.versionId;
    });
    const active = versionMap.get(entry.versionId) || versionMap.values().next().value || null;
    if (active) {
      applyOpacityToScene(active, 1, idx);
    }
    models[idx] = active;
    if (reload) {
      modelGroups[idx].visible = getVisibility(idx);
    }
  }

  function setModelVersionSelections(versionMap, { force = false } = {}) {
    if (!versionMap) return;
    Object.entries(versionMap).forEach(([id, value]) => {
      const match = /^glb_ver_(\d+)$/.exec(id);
      if (!match) return;
      const idx = Number.parseInt(match[1], 10);
      if (!Number.isInteger(idx)) return;
      setModelVersion(idx, value, { reload: false, force });
    });
  }

  function updateVisibility() {
    modelGroups.forEach((group, idx) => {
      if (group) group.visible = getVisibility(idx);
    });
  }

  function setModelOpacity(idx, opacity = 1) {
    const versionMap = modelVersionScenes[idx];
    const entry = modelEntries[idx];
    const scene = versionMap && entry ? versionMap.get(entry.versionId) : null;
    if (!scene) return;
    applyOpacityToScene(scene, opacity, idx);
  }

  function applyOpacityToScene(scene, opacity, idx) {
    const value = Math.max(0, Math.min(1, opacity));
    scene.renderOrder = value < 0.999 ? 100 + idx : 0;
    scene.traverse((child) => {
      if (!child.isMesh) return;
      const mat = child.material;
      const applyMat = (m) => {
        if (!m) return;
        if (!m.userData) m.userData = {};
        if (m.userData.baseOpacity === undefined) {
          m.userData.baseOpacity = Number.isFinite(m.opacity) ? m.opacity : 1;
        }
        m.transparent = true;
        m.depthWrite = value >= 0.999;
        m.depthTest = true;
        m.opacity = m.userData.baseOpacity * value;
        m.needsUpdate = true;
      };
      if (Array.isArray(mat)) {
        mat.forEach(applyMat);
      } else {
        applyMat(mat);
      }
      child.renderOrder = value < 0.999 ? 100 + idx : 0;
    });
  }

  function setModelVersionOpacity(idx, versionId, opacity = 1) {
    const versionMap = modelVersionScenes[idx];
    if (!versionMap) return;
    const scene = versionMap.get(versionId);
    if (!scene) return;
    scene.visible = opacity > 0;
    applyOpacityToScene(scene, opacity, idx);
  }

  function setModelVersionVisible(idx, versionId, visible) {
    const versionMap = modelVersionScenes[idx];
    if (!versionMap) return;
    const scene = versionMap.get(versionId);
    if (scene) scene.visible = !!visible;
  }

  function resetModelVersionOpacity(idx) {
    const versionMap = modelVersionScenes[idx];
    if (!versionMap) return;
    versionMap.forEach((scene) => {
      applyOpacityToScene(scene, 1, idx);
    });
  }

  function getModelCount() {
    return modelEntries.length;
  }

  function getModelVersionId(idx) {
    return modelEntries[idx]?.versionId || null;
  }


  function getBoundingBoxScene() {
    const bboxIdx = modelEntries.findIndex((entry) => entry.type === 'bounding box'
      || (entry.name || '').toLowerCase().includes('bounding box'));
    if (bboxIdx === -1) return null;
    const entry = modelEntries[bboxIdx];
    const versionMap = modelVersionScenes[bboxIdx];
    if (!entry || !versionMap) return null;
    return versionMap.get(entry.versionId) || null;
  }

  function buildVisibleGroup() {
    const group = new THREE.Group();
    for (let i = 0; i < modelGroups.length; i += 1) {
      if (modelGroups[i] && modelGroups[i].visible) {
        const entry = modelEntries[i];
        const versionMap = modelVersionScenes[i];
        const active = entry && versionMap ? versionMap.get(entry.versionId) : null;
        if (active) group.add(active.clone());
      }
    }
    return group.children.length > 0 ? group : null;
  }

  function getModelCenterWorld() {
    const bboxScene = getBoundingBoxScene();
    let target = null;
    if (bboxScene) {
      target = bboxScene;
    } else {
      target = buildVisibleGroup();
    }
    if (!target) return new THREE.Vector3();
    const box = new THREE.Box3().setFromObject(target);
    return box.getCenter(new THREE.Vector3());
  }

  function getModelCenterModel() {
    return world.worldToLocal(getModelCenterWorld().clone());
  }

  function getFrameBox(mode) {
    const bboxScene = getBoundingBoxScene();
    let target = null;
    if (mode === 'orthographic') {
      if (bboxScene) target = bboxScene;
    } else {
      if (bboxScene && bboxScene.visible) target = bboxScene;
    }
    if (!target) {
      const group = buildVisibleGroup();
      if (group) target = group;
    }
    if (!target) return null;
    return new THREE.Box3().setFromObject(target);
  }

  async function checkForUpdates() {
    const newList = await fetchModelList();
    if (!newList) {
      return { listChanged: false, filesChanged: false, error: 'offline' };
    }
    const newSignature = computeSignature(newList);

    if (newSignature !== listSignature) {
      return { listChanged: true, list: newList, signature: newSignature };
    }

    for (let i = 0; i < glbFiles.length; i += 1) {
      try {
        const response = await fetch(glbFiles[i].file, { method: 'HEAD', cache: 'no-store' });
        const newModified = response.headers.get('Last-Modified');
        if (lastModifieds[i] && newModified && newModified !== lastModifieds[i]) {
          lastModifieds[i] = newModified;
          return { listChanged: false, filesChanged: true };
        }
        if (!lastModifieds[i]) lastModifieds[i] = newModified;
      } catch (e) {
        // ignore
      }
    }

    return { listChanged: false, filesChanged: false };
  }

  return {
    fetchModelList,
    setModelList,
    getListSignature,
    getModelList,
    setDefaultVersionStrategy,
    applyDefaultVersionStrategy,
    getVersionSelections,
    loadAllModels,
    updateVisibility,
    checkForUpdates,
    getBoundingBoxScene,
    buildVisibleGroup,
    getFrameBox,
    getModelCenterWorld,
    getModelCenterModel,
    setVisibilityResolver,
    setVisibilityOverride,
    setVisibilityOverrides,
    clearVisibilityOverrides,
    setModelOpacity,
    setModelVersionOpacity,
    setModelVersionVisible,
    resetModelVersionOpacity,
    setModelVersion,
    setModelVersionSelections,
    getModelVersionId,
    getModelCount,
  };
}
