(function () {
  var STORAGE_KEY = 'docs-theme';

  function updateToggleLabel(theme) {
    var button = document.querySelector('.theme-toggle');
    if (!button) return;
    if (theme === 'dark') {
      button.textContent = '☀';
      button.setAttribute('aria-label', 'Switch to light theme');
      button.setAttribute('title', 'Switch to light theme');
    } else {
      button.textContent = '☾';
      button.setAttribute('aria-label', 'Switch to dark theme');
      button.setAttribute('title', 'Switch to dark theme');
    }
  }

  function setTheme(theme) {
    var root = document.documentElement;
    root.setAttribute('data-theme', theme);

    var links = Array.prototype.slice.call(document.querySelectorAll('link[rel="stylesheet"]'));
    var lightLink = links.find(function (link) {
      return link.href && link.href.indexOf('highlight.js@11.9.0/styles/vs.min.css') !== -1;
    });
    var darkLink = links.find(function (link) {
      return link.href && link.href.indexOf('highlight.js@11.9.0/styles/vs2015.min.css') !== -1;
    });

    if (lightLink) {
      lightLink.disabled = theme === 'dark';
    }
    if (darkLink) {
      darkLink.disabled = theme !== 'dark';
    }

    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // ignore storage errors
    }

    var event = new CustomEvent('themechange', { detail: { theme: theme } });
    window.dispatchEvent(event);

    updateToggleLabel(theme);
  }

  function getInitialTheme() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') return stored;
    } catch (e) {
      // ignore storage errors
    }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  function createToggle() {
    var button = document.createElement('button');
    button.className = 'theme-toggle';
    button.type = 'button';
    button.setAttribute('aria-label', 'Toggle theme');
    button.textContent = '☀';
    button.setAttribute('title', 'Toggle theme');
    button.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme') || 'light';
      setTheme(current === 'dark' ? 'light' : 'dark');
    });

    document.body.appendChild(button);
  }

  function applyThemeEarly() {
    var theme = getInitialTheme();
    document.documentElement.setAttribute('data-theme', theme);
  }

  function init() {
    setTheme(getInitialTheme());
    createToggle();
    updateToggleLabel(document.documentElement.getAttribute('data-theme') || 'light');
  }

  applyThemeEarly();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
