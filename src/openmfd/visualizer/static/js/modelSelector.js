const SELECTION_STORAGE_KEY = 'openmfd_model_selection_v2';
const COLLAPSED_STORAGE_KEY = 'openmfd_model_selector_collapsed';

function loadSelectionState() {
  const raw = localStorage.getItem(SELECTION_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

function saveSelectionState(state) {
  localStorage.setItem(SELECTION_STORAGE_KEY, JSON.stringify(state));
}

export function createModelSelector({ formEl, toggleBtn }) {
  let glbFiles = [];
  let listSignature = '';
  let onVisibilityChange = null;
  let onSelectionChange = null;
  let updateVisibilityFn = null;

  function setVisibilityCallback(callback) {
    onVisibilityChange = callback;
  }

  function setSelectionChangeCallback(callback) {
    onSelectionChange = callback;
  }

  function getSelectionSnapshot() {
    if (!formEl) return { models: {}, groups: {} };
    const modelMap = {};
    const groupMap = {};
    const modelCbs = formEl.querySelectorAll('input[data-model-idx]');
    modelCbs.forEach((cb) => {
      modelMap[cb.id] = cb.checked;
    });
    const groupCbs = formEl.querySelectorAll('input[data-group-id]');
    groupCbs.forEach((cb) => {
      groupMap[cb.id] = cb.checked;
    });
    return { models: modelMap, groups: groupMap };
  }

  function applySelectionSnapshot(snapshot, { persist = true } = {}) {
    if (!formEl || !snapshot) return;
    Object.entries(snapshot.models || {}).forEach(([id, checked]) => {
      const cb = document.getElementById(id);
      if (cb) cb.checked = checked;
    });
    Object.entries(snapshot.groups || {}).forEach(([id, checked]) => {
      const cb = document.getElementById(id);
      if (cb) cb.checked = checked;
    });
    if (updateVisibilityFn) {
      updateVisibilityFn();
    }
    if (persist) {
      persistSelection();
    }
  }

  function persistSelection() {
    if (!listSignature) return;
    const snapshot = getSelectionSnapshot();
    saveSelectionState({ signature: listSignature, ...snapshot });
  }

  function applySavedSelection() {
    const saved = loadSelectionState();
    if (!saved || saved.signature !== listSignature) return;
    Object.entries(saved.models || {}).forEach(([id, checked]) => {
      const cb = document.getElementById(id);
      if (cb) cb.checked = checked;
    });
    Object.entries(saved.groups || {}).forEach(([id, checked]) => {
      const cb = document.getElementById(id);
      if (cb) cb.checked = checked;
    });
  }

  function resetSelectionState() {
    localStorage.removeItem(SELECTION_STORAGE_KEY);
  }

  function build({ files, signature, resetSelection = false }) {
    if (!formEl) return;
    glbFiles = files || [];
    listSignature = signature || '';
    formEl.innerHTML = '';

    if (resetSelection) {
      resetSelectionState();
    }

    const groups = { bulk: [], void: [], regional: [], ports: [], device: [], 'bounding box': [] };
    const regionalSubgroups = {};

    glbFiles.forEach((glb, idx) => {
      let type = (glb.type || '').toLowerCase();
      if (type.startsWith('regional')) {
        let subtype = type.replace(/^regional[ _-]*/i, '').replace(/_/g, ' ');
        if (!subtype) subtype = 'other';
        if (!regionalSubgroups[subtype]) regionalSubgroups[subtype] = [];
        regionalSubgroups[subtype].push({ ...glb, idx });
        groups.regional.push({ ...glb, idx, _subtype: subtype });
      } else if (groups[type]) {
        groups[type].push({ ...glb, idx });
      } else {
        if (!groups.other) groups.other = [];
        groups.other.push({ ...glb, idx });
      }
    });

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
      if (meta.groupId) cb.dataset.groupId = meta.groupId;
      cb.style.marginRight = '0.5em';
      cb.addEventListener('change', () => {
        onChange();
        persistSelection();
      });
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
      const modelCbs = formEl.querySelectorAll('input[data-model-idx]');
      modelCbs.forEach((cb) => {
        const idx = Number(cb.dataset.modelIdx);
        const cbGroups = (cb.dataset.groups || '').split('|').filter(Boolean);
        const groupsOn = cbGroups.every(isGroupChecked);
        const visible = cb.checked && groupsOn;
        if (onVisibilityChange) {
          onVisibilityChange(idx, visible, cb);
        }
        const label = document.getElementById('glb_cb_label_' + idx);
        if (label) setLabelDisabled(label, !groupsOn);
      });

      const groupLabels = formEl.querySelectorAll('[data-group-label]');
      groupLabels.forEach((label) => {
        const parentGroup = label.dataset.parentGroup;
        const enabled = parentGroup ? isGroupChecked(parentGroup) : true;
        setLabelDisabled(label, !enabled);
      });

      if (onSelectionChange) {
        onSelectionChange(getSelectionSnapshot());
      }
    }

    updateVisibilityFn = updateVisibility;

    const topTypes = ['device', 'bounding box', 'ports'];
    topTypes.forEach((type) => {
      groups[type].forEach(({ name, idx }) => {
        const id = 'glb_cb_' + idx;
        const checked = true;
        const label = createCheckbox(id, checked, name, updateVisibility, {}, { modelIdx: idx, groups: [] });
        label.id = 'glb_cb_label_' + idx;
        formEl.appendChild(label);
      });
    });

    const expandableTypes = Object.keys(groups).filter((t) => !topTypes.includes(t));
    expandableTypes.forEach((type) => {
      if (!groups[type] || groups[type].length === 0) return;
      if (type === 'regional') {
        const groupId = 'group_cb_regional';
        const groupDiv = document.createElement('div');
        groupDiv.style.marginBottom = '0.5em';
        groupDiv.style.border = '1px solid #444';
        groupDiv.style.borderRadius = '0.3em';
        groupDiv.style.padding = '0.3em 0.5em';
        groupDiv.style.background = 'var(--section-bg)';

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
        groupLabel.textContent = `Regional (${groups[type].length})`;

        const groupCb = document.createElement('input');
        groupCb.type = 'checkbox';
        groupCb.id = groupId;
        groupCb.dataset.groupId = groupId;
        groupCb.checked = false;
        groupCb.style.marginRight = '0.5em';
        groupCb.addEventListener('change', () => {
          updateVisibility();
          persistSelection();
        });

        expBtn.addEventListener('click', () => {
          expanded = !expanded;
          expBtn.textContent = expanded ? '▼' : '►';
          groupContent.style.display = expanded ? '' : 'none';
        });

        const groupHeader = document.createElement('div');
        groupHeader.style.display = 'flex';
        groupHeader.style.alignItems = 'center';
        groupHeader.appendChild(expBtn);
        groupHeader.appendChild(groupCb);
        groupHeader.appendChild(groupLabel);
        groupDiv.appendChild(groupHeader);

        const groupContent = document.createElement('div');
        groupContent.style.display = 'none';
        groupContent.style.marginLeft = '1.5em';

        Object.entries(regionalSubgroups).forEach(([subtype, models]) => {
          const subGroupId = 'group_cb_regional_' + subtype.replace(/\s+/g, '_');
          const subGroupDiv = document.createElement('div');
          subGroupDiv.style.marginBottom = '0.3em';

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
          subGroupCb.dataset.groupId = subGroupId;
          subGroupCb.checked = true;
          subGroupCb.style.marginRight = '0.5em';
          subGroupCb.addEventListener('change', () => {
            updateVisibility();
            persistSelection();
          });

          const subGroupLabel = document.createElement('span');
          subGroupLabel.id = subGroupId + '_label';
          subGroupLabel.dataset.groupLabel = 'true';
          subGroupLabel.dataset.parentGroup = groupId;
          subGroupLabel.textContent = `${subtype.charAt(0).toUpperCase() + subtype.slice(1)} (${models.length})`;

          subGroupHeader.appendChild(subExpBtn);
          subGroupHeader.appendChild(subGroupCb);
          subGroupHeader.appendChild(subGroupLabel);
          subGroupDiv.appendChild(subGroupHeader);

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
            const label = createCheckbox(id, checked, name, updateVisibility, {}, { modelIdx: idx, groups: [groupId, subGroupId] });
            label.id = 'glb_cb_label_' + idx;
            subGroupContent.appendChild(label);
          });

          subGroupDiv.appendChild(subGroupContent);
          groupContent.appendChild(subGroupDiv);
        });

        groupDiv.appendChild(groupContent);
        formEl.appendChild(groupDiv);
        return;
      }

      const groupId = 'group_cb_' + type;
      const groupDiv = document.createElement('div');
      groupDiv.style.marginBottom = '0.5em';
      groupDiv.style.border = '1px solid #444';
      groupDiv.style.borderRadius = '0.3em';
      groupDiv.style.padding = '0.3em 0.5em';
      groupDiv.style.background = 'var(--section-bg)';

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
      groupLabel.textContent = `${type.charAt(0).toUpperCase() + type.slice(1)} (${groups[type].length})`;

      const groupCb = document.createElement('input');
      groupCb.type = 'checkbox';
      groupCb.id = groupId;
      groupCb.dataset.groupId = groupId;
      groupCb.checked = false;
      groupCb.style.marginRight = '0.5em';
      groupCb.addEventListener('change', () => {
        updateVisibility();
        persistSelection();
      });

      expBtn.addEventListener('click', () => {
        expanded = !expanded;
        expBtn.textContent = expanded ? '▼' : '►';
        groupContent.style.display = expanded ? '' : 'none';
      });

      const groupHeader = document.createElement('div');
      groupHeader.style.display = 'flex';
      groupHeader.style.alignItems = 'center';
      groupHeader.appendChild(expBtn);
      groupHeader.appendChild(groupCb);
      groupHeader.appendChild(groupLabel);
      groupDiv.appendChild(groupHeader);

      const groupContent = document.createElement('div');
      groupContent.style.display = 'none';
      groupContent.style.marginLeft = '1.5em';

      groups[type].forEach(({ name, idx }) => {
        const id = 'glb_cb_' + idx;
        const checked = true;
        const label = createCheckbox(id, checked, name, updateVisibility, {}, { modelIdx: idx, groups: [groupId] });
        label.id = 'glb_cb_label_' + idx;
        groupContent.appendChild(label);
      });

      groupDiv.appendChild(groupContent);
      formEl.appendChild(groupDiv);
    });

    if (toggleBtn) {
      const savedCollapsed = localStorage.getItem(COLLAPSED_STORAGE_KEY);
      const isCollapsed = savedCollapsed === 'true';
      formEl.style.display = isCollapsed ? 'none' : '';
      toggleBtn.textContent = isCollapsed ? '+' : '–';
      toggleBtn.onclick = () => {
        const nextCollapsed = formEl.style.display !== 'none';
        formEl.style.display = nextCollapsed ? 'none' : '';
        toggleBtn.textContent = nextCollapsed ? '+' : '–';
        localStorage.setItem(COLLAPSED_STORAGE_KEY, String(nextCollapsed));
      };
    }

    applySavedSelection();
    updateVisibility();
    persistSelection();
  }

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

  return {
    build,
    getModelVisibility,
    setVisibilityCallback,
    setSelectionChangeCallback,
    resetSelectionState,
    getSelectionSnapshot,
    applySelectionSnapshot,
  };
}
