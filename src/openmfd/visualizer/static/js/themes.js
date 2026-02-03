import * as THREE from '../lib/three/three.module.js';

const THEME_STORAGE_KEY = 'openmfd_theme';
const THEME_DEFS_KEY = 'openmfd_theme_defs_v1';

const DEFAULT_THEMES = {
  dark: {
    '--bg': '#222222',
    '--panel': '#222222',
    '--section-bg': '#1a1a1a',
    '--text': '#ffffff',
    '--button-bg': '#3a3a3a',
    '--button-text': '#ffffff',
    '--button-border': '#555555',
    '--button-bg-active': '#888888',
    '--axis-x': '#aa4444',
    '--axis-y': '#44aa44',
    '--axis-z': '#4444aa',
  },
  light: {
    '--bg': '#f5f5f5',
    '--panel': '#ffffff',
    '--section-bg': '#f0f0f0',
    '--text': '#111111',
    '--button-bg': '#ffffff',
    '--button-text': '#111111',
    '--button-border': '#bbbbbb',
    '--button-bg-active': '#f0f0f0',
    '--axis-x': '#dd0000',
    '--axis-y': '#00aa00',
    '--axis-z': '#0000cc',
  },
  custom: {
    '--bg': '#1f1f1f',
    '--panel': '#2a2a2a',
    '--section-bg': '#1a1a1a',
    '--text': '#f5f5f5',
    '--button-bg': '#3d3d3d',
    '--button-text': '#f5f5f5',
    '--button-border': '#5a5a5a',
    '--button-bg-active': '#7a7a7a',
    '--axis-x': '#aa4444',
    '--axis-y': '#44aa44',
    '--axis-z': '#4444aa',
  },
};

function loadThemeDefs() {
  const raw = localStorage.getItem(THEME_DEFS_KEY);
  if (!raw) return { ...DEFAULT_THEMES };
  try {
    const parsed = JSON.parse(raw);
    return {
      dark: { ...DEFAULT_THEMES.dark, ...(parsed.dark || {}) },
      light: { ...DEFAULT_THEMES.light, ...(parsed.light || {}) },
      custom: { ...DEFAULT_THEMES.custom, ...(parsed.custom || {}) },
    };
  } catch (e) {
    return { ...DEFAULT_THEMES };
  }
}

function saveThemeDefs(defs) {
  localStorage.setItem(THEME_DEFS_KEY, JSON.stringify(defs));
}

function applyThemeVars(vars) {
  const root = document.documentElement;
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
}

function updateAxesColors(axes, vars) {
  if (!axes || !axes.setColors) return;
  const parse = (value, fallback) => {
    if (!value) return fallback;
    return Number.parseInt(value.replace('#', ''), 16);
  };
  const x = parse(vars['--axis-x'], 0xaa4444);
  const y = parse(vars['--axis-y'], 0x44aa44);
  const z = parse(vars['--axis-z'], 0x4444aa);
  axes.setColors(x, y, z);
}

export function createThemeManager({ scene, axes }) {
  let themes = loadThemeDefs();
  let activeTheme = localStorage.getItem(THEME_STORAGE_KEY) || 'dark';

  function applyTheme(themeName) {
    if (!themes[themeName]) return;
    activeTheme = themeName;
    localStorage.setItem(THEME_STORAGE_KEY, themeName);
    applyThemeVars(themes[themeName]);
    const bg = themes[themeName]['--bg'] || '#222222';
    scene.background = new THREE.Color(bg);
    updateAxesColors(axes, themes[themeName]);
    window.dispatchEvent(new CustomEvent('openmfd-theme-changed', {
      detail: {
        theme: themeName,
        vars: { ...themes[themeName] },
      },
    }));
  }

  function resetTheme(themeName) {
    if (!DEFAULT_THEMES[themeName]) return;
    themes = { ...themes, [themeName]: { ...DEFAULT_THEMES[themeName] } };
    saveThemeDefs(themes);
    if (activeTheme === themeName) {
      applyTheme(themeName);
    }
  }

  function resetAllThemes() {
    themes = { ...DEFAULT_THEMES };
    saveThemeDefs(themes);
    activeTheme = 'dark';
    localStorage.setItem(THEME_STORAGE_KEY, activeTheme);
    applyTheme(activeTheme);
  }

  function updateThemeValue(themeName, key, value) {
    if (!themes[themeName]) return;
    themes[themeName] = { ...themes[themeName], [key]: value };
    saveThemeDefs(themes);
    if (activeTheme === themeName) {
      applyTheme(themeName);
    }
  }

  function saveAsCustom(sourceTheme) {
    if (!themes[sourceTheme]) return;
    themes.custom = { ...themes[sourceTheme] };
    saveThemeDefs(themes);
    applyTheme('custom');
  }

  function initTheme() {
    applyTheme(activeTheme);
  }

  function bindThemeUI({
    themeSelect,
    themeInputs,
    resetBtn,
    saveCustomBtn,
    resetAllBtn,
  }) {
    if (!themeSelect || !themeInputs) return;

    function syncInputs(themeName) {
      const theme = themes[themeName];
      if (!theme) return;
      Object.entries(themeInputs).forEach(([key, input]) => {
        if (input) input.value = theme[key] || DEFAULT_THEMES.dark[key] || '#000000';
      });
    }

    themeSelect.value = themes[activeTheme] ? activeTheme : 'dark';
    syncInputs(themeSelect.value);

    themeSelect.addEventListener('change', () => {
      const nextTheme = themeSelect.value;
      applyTheme(nextTheme);
      syncInputs(nextTheme);
    });

    Object.entries(themeInputs).forEach(([key, input]) => {
      if (!input) return;
      input.addEventListener('input', () => {
        updateThemeValue(themeSelect.value, key, input.value);
      });
    });

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        resetTheme(themeSelect.value);
        syncInputs(themeSelect.value);
      });
    }

    if (resetAllBtn) {
      resetAllBtn.addEventListener('click', () => {
        resetAllThemes();
        themeSelect.value = activeTheme;
        syncInputs(activeTheme);
      });
    }

    if (saveCustomBtn) {
      saveCustomBtn.addEventListener('click', () => {
        saveAsCustom(themeSelect.value);
        themeSelect.value = 'custom';
        syncInputs('custom');
      });
    }
  }

  return {
    initTheme,
    applyTheme,
    bindThemeUI,
    resetAllThemes,
    getThemeState: () => ({
      activeTheme,
      themes: { ...themes },
    }),
    setThemeState: (state) => {
      if (!state || typeof state !== 'object') return;
      const incomingThemes = state.themes || state.themeDefs;
      if (incomingThemes && typeof incomingThemes === 'object') {
        themes = {
          dark: { ...DEFAULT_THEMES.dark, ...(incomingThemes.dark || {}) },
          light: { ...DEFAULT_THEMES.light, ...(incomingThemes.light || {}) },
          custom: { ...DEFAULT_THEMES.custom, ...(incomingThemes.custom || {}) },
        };
        saveThemeDefs(themes);
      }
      if (state.activeTheme && themes[state.activeTheme]) {
        activeTheme = state.activeTheme;
      } else {
        activeTheme = localStorage.getItem(THEME_STORAGE_KEY) || activeTheme;
      }
      applyTheme(activeTheme);
    },
  };
}
