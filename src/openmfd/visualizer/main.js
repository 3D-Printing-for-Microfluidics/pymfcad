
import * as THREE from './visualizer/three/three.module.js';
import { OrbitControls } from './visualizer/three/controls/OrbitControls.js';
import { GLTFLoader } from './visualizer/three/loaders/GLTFLoader.js';

// Dynamically load GLB file list from server
let glbFiles = [];
let defaultCamPos = new THREE.Vector3();
let defaultCamTarget = new THREE.Vector3();

// Model management
const loader = new GLTFLoader();
let models = [];
let modelGroups = [];
let lastModifieds = [];

function getModelVisibility(idx) {
    const cb = document.getElementById('glb_cb_' + idx);
    if (!cb) return true;
    const groups = (cb.dataset.groups || '').split('|').filter(Boolean);
    const groupsOn = groups.every((groupId) => {
        const groupCb = document.getElementById(groupId);
        return groupCb ? groupCb.checked : true;
    });
    return cb.checked && groupsOn;
}

// Load all models
function loadAllModels(preserveCamera = false) {
    console.log("\tLoading all models...");
    // Remove and dispose all old models (even if new list is shorter)
    if (modelGroups && modelGroups.length) {
        for (let group of modelGroups) {
            if (group && group.parent === world) world.remove(group);
            if (group) {
                group.traverse((child) => {
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) {
                        if (Array.isArray(child.material)) {
                            child.material.forEach(m => m.dispose());
                        } else {
                            child.material.dispose();
                        }
                    }
                });
            }
        }
    }
    models = [];
    modelGroups = [];
    lastModifieds = Array(glbFiles.length).fill(null);

    let loadedCount = 0;
    let totalToLoad = glbFiles.length;
    let loadedScenes = Array(glbFiles.length).fill(null);
    glbFiles.forEach((glb, idx) => {
        const cacheBuster = `?cb=${Date.now()}`;
        console.log("\t\tLoading GLB:", glb.file);
        loader.load(glb.file + cacheBuster, (gltf) => {
            gltf.scene.traverse((child) => {
                if (child.isMesh) {
                    let mat = child.material;
                    mat.metalness = 0.5;
                    mat.transparent = true;
                    mat.side = THREE.FrontSide;
                }
            });
            models[idx] = gltf.scene;
            modelGroups[idx] = gltf.scene;
            loadedScenes[idx] = gltf.scene;
            // Set initial visibility from checkbox
            gltf.scene.visible = getModelVisibility(idx);
            world.add(gltf.scene);
            loadedCount++;
            // After all models are loaded, frame camera
            if (!preserveCamera && loadedCount === totalToLoad) {
                resetCamera();
            }
        }, undefined, (err) => {
            // Optionally handle errors
        });
    });
}

// Build model selector widget
function buildModelSelector() {
    const form = document.getElementById('glbForm');
    const toggleBtn = document.getElementById('toggleModelSelectorBtn');
    form.innerHTML = '';
    // Group models by type
    const groups = { bulk: [], void: [], regional: [], ports: [], device: [], "bounding box": [] };
    // For regional, further group by subtype (from type string)
    const regionalSubgroups = {};
    glbFiles.forEach((glb, idx) => {
        let type = (glb.type || '').toLowerCase();
        if (type.startsWith('regional')) {
            // Extract subgroup: e.g. 'regional membrane settings' -> 'membrane settings'
            let subtype = type.replace(/^regional[ _-]*/i, '').replace(/_/g, ' ');
            if (!subtype) subtype = 'other';
            if (!regionalSubgroups[subtype]) regionalSubgroups[subtype] = [];
            regionalSubgroups[subtype].push({ ...glb, idx });
            groups['regional'].push({ ...glb, idx, _subtype: subtype });
        } else if (groups[type]) {
            groups[type].push({ ...glb, idx });
        } else {
            if (!groups.other) groups.other = [];
            groups.other.push({ ...glb, idx });
        }
    });

    // Helper to create a checkbox
    function createCheckbox(id, checked, labelText, onChange, style = {}, meta = {}) {
        const label = document.createElement('label');
        label.style.display = 'block';
        label.style.marginBottom = '0.25em';
        Object.assign(label.style, style);
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = id;
        cb.checked = checked;
        if (meta.modelIdx !== undefined) cb.dataset.modelIdx = String(meta.modelIdx);
        if (meta.groups) cb.dataset.groups = meta.groups.join('|');
        cb.style.marginRight = '0.5em';
        cb.addEventListener('change', onChange);
        label.appendChild(cb);
        label.appendChild(document.createTextNode(labelText));
        return label;
    }

    function setLabelDisabled(labelEl, disabled) {
        labelEl.style.opacity = disabled ? '0.5' : '1';
    }

    function isGroupChecked(groupId) {
        if (!groupId) return true;
        const cb = document.getElementById(groupId);
        return cb ? cb.checked : true;
    }

    function updateVisibility() {
        const modelCbs = form.querySelectorAll('input[data-model-idx]');
        modelCbs.forEach((cb) => {
            const idx = Number(cb.dataset.modelIdx);
            const groups = (cb.dataset.groups || '').split('|').filter(Boolean);
            const groupsOn = groups.every(isGroupChecked);
            const visible = cb.checked && groupsOn;
            if (modelGroups[idx]) modelGroups[idx].visible = visible;
            const label = document.getElementById('glb_cb_label_' + idx);
            if (label) setLabelDisabled(label, !groupsOn);
        });

        const groupLabels = form.querySelectorAll('[data-group-label]');
        groupLabels.forEach((label) => {
            const parentGroup = label.dataset.parentGroup;
            const enabled = parentGroup ? isGroupChecked(parentGroup) : true;
            setLabelDisabled(label, !enabled);
        });
    }

    // Top-level: device, bounding box, ports
    const topTypes = ['device', 'bounding box', 'ports'];
    topTypes.forEach(type => {
        groups[type].forEach(({ name, idx }) => {
            const id = 'glb_cb_' + idx;
            // Only show these by default
            const checked = true;
            const label = createCheckbox(
                id,
                checked,
                name,
                updateVisibility,
                {},
                { modelIdx: idx, groups: [] }
            );
            label.id = 'glb_cb_label_' + idx;
            form.appendChild(label);
        });
    });

    // Expandable groups for bulk, void, other
    const expandableTypes = Object.keys(groups).filter(t => !topTypes.includes(t));
    expandableTypes.forEach(type => {
        if (!groups[type] || groups[type].length === 0) return;
        // Special handling for regional
        if (type === 'regional') {
            // Regional group master
            const groupId = 'group_cb_regional';
            const groupDiv = document.createElement('div');
            groupDiv.style.marginBottom = '0.5em';
            groupDiv.style.border = '1px solid #444';
            groupDiv.style.borderRadius = '0.3em';
            groupDiv.style.padding = '0.3em 0.5em';
            groupDiv.style.background = 'rgba(0,0,0,0.10)';
            // Expand/collapse
            const expBtn = document.createElement('button');
            expBtn.type = 'button';
            expBtn.textContent = '►';
            expBtn.style.marginRight = '0.5em';
            expBtn.style.background = 'none';
            expBtn.style.border = 'none';
            expBtn.style.color = '#fff';
            expBtn.style.cursor = 'pointer';
            expBtn.style.fontWeight = 'bold';
            let expanded = false;
            const groupLabel = document.createElement('span');
            groupLabel.dataset.groupLabel = 'true';
            groupLabel.textContent = 'Regional (' + groups[type].length + ')';
            const groupCb = document.createElement('input');
            groupCb.type = 'checkbox';
            groupCb.id = groupId;
            groupCb.checked = false;
            groupCb.style.marginRight = '0.5em';
            groupCb.addEventListener('change', updateVisibility);
            // Expand/collapse logic
            expBtn.addEventListener('click', () => {
                expanded = !expanded;
                expBtn.textContent = expanded ? '▼' : '►';
                groupContent.style.display = expanded ? '' : 'none';
            });
            // Group header
            const groupHeader = document.createElement('div');
            groupHeader.style.display = 'flex';
            groupHeader.style.alignItems = 'center';
            groupHeader.appendChild(expBtn);
            groupHeader.appendChild(groupCb);
            groupHeader.appendChild(groupLabel);
            groupDiv.appendChild(groupHeader);
            // Group content (subgroups)
            const groupContent = document.createElement('div');
            groupContent.style.display = 'none';
            expBtn.textContent = expanded ? '▼' : '►';
            groupContent.style.marginLeft = '1.5em';
            Object.entries(regionalSubgroups).forEach(([subtype, models]) => {
                // Subgroup master
                const subGroupId = 'group_cb_regional_' + subtype.replace(/\s+/g, '_');
                const subGroupDiv = document.createElement('div');
                subGroupDiv.style.marginBottom = '0.3em';
                // Subgroup header
                const subGroupHeader = document.createElement('div');
                subGroupHeader.style.display = 'flex';
                subGroupHeader.style.alignItems = 'center';
                const subExpBtn = document.createElement('button');
                subExpBtn.type = 'button';
                subExpBtn.textContent = '►';
                subExpBtn.style.marginRight = '0.5em';
                subExpBtn.style.background = 'none';
                subExpBtn.style.border = 'none';
                subExpBtn.style.color = '#fff';
                subExpBtn.style.cursor = 'pointer';
                subExpBtn.style.fontWeight = 'bold';
                const subGroupCb = document.createElement('input');
                subGroupCb.type = 'checkbox';
                subGroupCb.id = subGroupId;
                subGroupCb.checked = true;
                subGroupCb.style.marginRight = '0.5em';
                subGroupCb.addEventListener('change', updateVisibility);
                const subGroupLabel = document.createElement('span');
                subGroupLabel.id = subGroupId + '_label';
                subGroupLabel.dataset.groupLabel = 'true';
                subGroupLabel.dataset.parentGroup = groupId;
                subGroupLabel.textContent = subtype.charAt(0).toUpperCase() + subtype.slice(1) + ' (' + models.length + ')';
                subGroupHeader.appendChild(subExpBtn);
                subGroupHeader.appendChild(subGroupCb);
                subGroupHeader.appendChild(subGroupLabel);
                subGroupDiv.appendChild(subGroupHeader);
                // Subgroup content
                const subGroupContent = document.createElement('div');
                subGroupContent.style.marginLeft = '1.5em';
                subGroupContent.style.display = 'none';
                subExpBtn.addEventListener('click', () => {
                    const isOpen = subGroupContent.style.display !== 'none';
                    subGroupContent.style.display = isOpen ? 'none' : '';
                    subExpBtn.textContent = isOpen ? '►' : '▼';
                });
                models.forEach(({ name, idx }) => {
                    const id = 'glb_cb_' + idx;
                    const checked = true;
                    const label = createCheckbox(
                        id,
                        checked,
                        name,
                        updateVisibility,
                        {},
                        { modelIdx: idx, groups: [groupId, subGroupId] }
                    );
                    label.id = 'glb_cb_label_' + idx;
                    subGroupContent.appendChild(label);
                });
                subGroupDiv.appendChild(subGroupContent);
                groupContent.appendChild(subGroupDiv);
            });
            groupDiv.appendChild(groupContent);
            form.appendChild(groupDiv);
            updateVisibility();
            return;
        }
        // Default: non-regional expandable group
        // Group master checkbox
        const groupId = 'group_cb_' + type;
        const groupDiv = document.createElement('div');
        groupDiv.style.marginBottom = '0.5em';
        groupDiv.style.border = '1px solid #444';
        groupDiv.style.borderRadius = '0.3em';
        groupDiv.style.padding = '0.3em 0.5em';
        groupDiv.style.background = 'rgba(0,0,0,0.10)';
        // Expand/collapse
        const expBtn = document.createElement('button');
        expBtn.type = 'button';
        expBtn.textContent = '►';
        expBtn.style.marginRight = '0.5em';
        expBtn.style.background = 'none';
        expBtn.style.border = 'none';
        expBtn.style.color = '#fff';
        expBtn.style.cursor = 'pointer';
        expBtn.style.fontWeight = 'bold';
        let expanded = false;
        const groupLabel = document.createElement('span');
        groupLabel.dataset.groupLabel = 'true';
        groupLabel.textContent = type.charAt(0).toUpperCase() + type.slice(1) + ' (' + groups[type].length + ')';
        const groupCb = document.createElement('input');
        groupCb.type = 'checkbox';
        groupCb.id = groupId;
        groupCb.checked = false;
        groupCb.style.marginRight = '0.5em';
        groupCb.addEventListener('change', updateVisibility);
        // Expand/collapse logic
        expBtn.addEventListener('click', () => {
            expanded = !expanded;
            expBtn.textContent = expanded ? '▼' : '►';
            groupContent.style.display = expanded ? '' : 'none';
        });
        // Group header
        const groupHeader = document.createElement('div');
        groupHeader.style.display = 'flex';
        groupHeader.style.alignItems = 'center';
        groupHeader.appendChild(expBtn);
        groupHeader.appendChild(groupCb);
        groupHeader.appendChild(groupLabel);
        groupDiv.appendChild(groupHeader);
        // Group content
        const groupContent = document.createElement('div');
        groupContent.style.display = 'none';
        expBtn.textContent = expanded ? '▼' : '►';
        groupContent.style.marginLeft = '1.5em';
        groups[type].forEach(({ name, idx }) => {
            const id = 'glb_cb_' + idx;
            // Not checked by default
            const checked = true;
            const label = createCheckbox(
                id,
                checked,
                name,
                updateVisibility,
                {},
                { modelIdx: idx, groups: [groupId] }
            );
            label.id = 'glb_cb_label_' + idx;
            groupContent.appendChild(label);
        });
        groupDiv.appendChild(groupContent);
        form.appendChild(groupDiv);
        updateVisibility();
    });

    const savedCollapsed = localStorage.getItem('openmfd_model_selector_collapsed');
    const isCollapsed = savedCollapsed === 'true';
    if (toggleBtn) {
        form.style.display = isCollapsed ? 'none' : '';
        toggleBtn.textContent = isCollapsed ? '+' : '–';
        toggleBtn.onclick = () => {
            const nextCollapsed = form.style.display !== 'none' ? true : false;
            form.style.display = nextCollapsed ? 'none' : '';
            toggleBtn.textContent = nextCollapsed ? '+' : '–';
            localStorage.setItem('openmfd_model_selector_collapsed', String(nextCollapsed));
        };
    }

    updateVisibility();
}

// Watch for GLB file changes and model list changes
let lastModelListString = '';
let models_changed = false;
let autoReloadEnabled = true;
let autoReloadInterval = null;

async function checkGLBUpdates() {
    console.log("\tChecking for GLB updates...");
    // Check if the model list has changed
    let newList = null;
    try {
        const resp = await fetch('/glb_list.json', { cache: 'no-store' });
        newList = await resp.json();
    } catch (e) {
        newList = glbFiles;
    }
    const newListString = JSON.stringify(newList);
    if (newListString !== lastModelListString) {
        models_changed = true;
        glbFiles = newList;
        lastModelListString = newListString;
        return;
    }
    if (models_changed) {
        console.log("\tModel list changed, reloading models...");
        models_changed = false;
        glbFiles = newList;
        lastModelListString = newListString;
        buildModelSelector();
        loadAllModels(true);
        return;
    }
    // If model list is the same, check for file updates
    for (let i = 0; i < glbFiles.length; ++i) {
        try {
            const response = await fetch(glbFiles[i].file, { method: 'HEAD', cache: 'no-store' });
            const newModified = response.headers.get('Last-Modified');
            if (lastModifieds[i] && newModified && newModified !== lastModifieds[i]) {
                console.log(`\tGLB file updated: ${glbFiles[i].file}, reloading models...`);
                lastModifieds[i] = newModified;
                loadAllModels(true);
                break;
            }
            if (!lastModifieds[i]) lastModifieds[i] = newModified;
        } catch (e) { }
    }
}

// Fetch the GLB file list and initialize visualizer
async function initVisualizer() {
    console.log("Initializing OpenMFD Visualizer...");
    try {
        const resp = await fetch('/glb_list.json');
        glbFiles = await resp.json();
        lastModelListString = JSON.stringify(glbFiles);
        console.log("GLB Files:", glbFiles);
    } catch (e) {
        glbFiles = [];
        lastModelListString = '';
    }
    console.log("Building model selector...");
    buildModelSelector();
    console.log("Loading models...");
    loadAllModels();
    // Start auto-reload if enabled
    if (autoReloadEnabled) {
        autoReloadInterval = setInterval(checkGLBUpdates, 1000);
    }
}

// Call initialization
initVisualizer();

function frameModel(object, camera, controls, offset = 1.25) {
    console.log("Framing model...");
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxSize = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    let distance = maxSize / (2 * Math.tan(fov / 2));
    distance *= offset;
    const direction = new THREE.Vector3(0.5, 0.5, 1).normalize();
    camera.position.copy(center).add(direction.multiplyScalar(distance));
    controls.target.copy(center);
    controls.update();
    camera.updateProjectionMatrix();
}

function resetCamera() {
    // Recalculate camera position based on newest models
    // Try to frame bounding_box.glb if present and visible
    let bboxIdx = glbFiles.findIndex(f => f.file.toLowerCase().includes('bounding_box.glb'));
    let bboxScene = (bboxIdx !== -1 && modelGroups[bboxIdx] && modelGroups[bboxIdx].visible) ? modelGroups[bboxIdx] : null;
    if (bboxScene) {
        frameModel(bboxScene, camera, controls);
    } else {
        // Frame all visible models
        let group = new THREE.Group();
        for (let i = 0; i < modelGroups.length; ++i) {
            if (modelGroups[i] && modelGroups[i].visible) group.add(modelGroups[i].clone());
        }
        if (group.children.length > 0) {
            frameModel(group, camera, controls);
        }
    }
    defaultCamPos.copy(camera.position);
    defaultCamTarget.copy(controls.target);
    controls.update();
}

// Create Scene
const scene = new THREE.Scene();

function getCssVar(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
}

function applyTheme(theme) {
    if (theme === 'light') {
        document.body.classList.add('theme-light');
    } else {
        document.body.classList.remove('theme-light');
    }
    localStorage.setItem('openmfd_theme', theme);
    const bg = getCssVar('--bg') || '#222222';
    scene.background = new THREE.Color(bg);
    if (axes && axes.setColors) {
        if (theme === 'light') {
            axes.setColors(0xDD0000, 0x00AA00, 0x0000CC);
        } else {
            axes.setColors(0xAA4444, 0x44AA44, 0x4444AA);
        }
    }
}

function initTheme() {
    const saved = localStorage.getItem('openmfd_theme');
    const theme = saved === 'light' ? 'light' : 'dark';
    applyTheme(theme);
    const btn = document.getElementById('themeToggleBtn');
    if (btn) {
        btn.textContent = theme === 'light' ? 'Theme: Light' : 'Theme: Dark';
    }
}
const world = new THREE.Group();
scene.add(world);
world.rotation.x = -Math.PI / 2;
const axes = new THREE.AxesHelper(100);
axes.position.set(-0.0001, -0.0001, -0.0001);
world.add(axes);
const light = new THREE.DirectionalLight(0xffffff, 1.0);
light.position.set(10, 10, 10);
world.add(light);
world.add(new THREE.AmbientLight(0xffffff, 1.0));
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

document.getElementById('resetCameraBtn').addEventListener('click', () => {
    resetCamera();
});

const reloadModelBtn = document.getElementById('reloadModelBtn');
reloadModelBtn.textContent = 'Auto Reload: ON';
reloadModelBtn.classList.add('is-active');

reloadModelBtn.addEventListener('click', () => {
    autoReloadEnabled = !autoReloadEnabled;
    if (autoReloadEnabled) {
        reloadModelBtn.textContent = 'Auto Reload: ON';
        reloadModelBtn.classList.add('is-active');
        if (!autoReloadInterval) {
            autoReloadInterval = setInterval(checkGLBUpdates, 1000);
        }
    } else {
        reloadModelBtn.textContent = 'Auto Reload: OFF';
        reloadModelBtn.classList.remove('is-active');
        if (autoReloadInterval) {
            clearInterval(autoReloadInterval);
            autoReloadInterval = null;
        }
    }
});

const themeToggleBtn = document.getElementById('themeToggleBtn');
if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        const current = localStorage.getItem('openmfd_theme') === 'light' ? 'light' : 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
        themeToggleBtn.textContent = next === 'light' ? 'Theme: Light' : 'Theme: Dark';
    });
}

const toggleAxesBtn = document.getElementById('toggleAxesBtn');
if (toggleAxesBtn) {
    const savedAxes = localStorage.getItem('openmfd_axes_visible');
    axes.visible = savedAxes !== 'false';
    toggleAxesBtn.textContent = axes.visible ? 'Axes: On' : 'Axes: Off';
    toggleAxesBtn.addEventListener('click', () => {
        axes.visible = !axes.visible;
        localStorage.setItem('openmfd_axes_visible', String(axes.visible));
        toggleAxesBtn.textContent = axes.visible ? 'Axes: On' : 'Axes: Off';
    });
}

initTheme();