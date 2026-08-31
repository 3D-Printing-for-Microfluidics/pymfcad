(function () {
  function getTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  }

  function syncThemeImages() {
    var theme = getTheme();
    document.querySelectorAll("img[data-light-src][data-dark-src]").forEach(function (img) {
      var nextSrc = theme === "dark" ? img.dataset.darkSrc : img.dataset.lightSrc;
      if (nextSrc && img.getAttribute("src") !== nextSrc) {
        img.setAttribute("src", nextSrc);
      }
    });
  }

  function init() {
    syncThemeImages();
    window.addEventListener("themechange", syncThemeImages);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();