(function (global) {
  var KEY = 'enact-theme';
  var MODES = ["light", "dark", "system"];

  function resolveTheme(mode, prefersDark) {
    if (mode === "dark") return "dark";
    if (mode === "light") return "light";
    return prefersDark ? "dark" : "light";
  }

  function readMode(storage) {
    try {
      var stored = storage && storage.getItem(KEY);
      if (stored === "light" || stored === "dark" || stored === "system") return stored;
    } catch (err) {}
    return "system";
  }

  function writeMode(storage, mode) {
    if (MODES.indexOf(mode) === -1) mode = "system";
    try {
      if (storage) storage.setItem(KEY, mode);
    } catch (err) {}
    return mode;
  }

  function apply(doc, mode, prefersDark) {
    var theme = resolveTheme(mode, !!prefersDark);
    var root = doc.documentElement;
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-theme-mode", mode);
    root.style.colorScheme = theme;
    return theme;
  }

  function mediaMatches(media) {
    return !!(media && media.matches);
  }

  function currentMedia() {
    return global.matchMedia ? global.matchMedia("(prefers-color-scheme: dark)") : { matches: false };
  }

  function syncToggle(doc, mode) {
    var buttons = doc.querySelectorAll("[data-theme-choice]");
    for (var i = 0; i < buttons.length; i += 1) {
      var choice = buttons[i].getAttribute("data-theme-choice") || buttons[i].dataset.themeChoice;
      var on = choice === mode;
      buttons[i].setAttribute("aria-checked", on ? "true" : "false");
      buttons[i].tabIndex = on ? 0 : -1;
    }
  }

  function boot(doc, storage, media) {
    var mode = readMode(storage);
    apply(doc, mode, mediaMatches(media));
    syncToggle(doc, mode);
    return mode;
  }

  function setMode(doc, storage, media, mode) {
    mode = writeMode(storage, mode);
    apply(doc, mode, mediaMatches(media));
    syncToggle(doc, mode);
    return mode;
  }

  function bindToggle(doc, storage, media) {
    var buttons = Array.prototype.slice.call(doc.querySelectorAll("[data-theme-choice]"));
    if (!buttons.length) return;
    buttons.forEach(function (btn, index) {
      if (!btn || typeof btn.addEventListener !== "function") return;
      btn.addEventListener("click", function () {
        setMode(doc, storage, media, btn.getAttribute("data-theme-choice"));
      });
      btn.addEventListener("keydown", function (event) {
        var key = event.key;
        var next = index;
        if (key === "ArrowRight" || key === "ArrowDown") next = (index + 1) % buttons.length;
        else if (key === "ArrowLeft" || key === "ArrowUp") next = (index - 1 + buttons.length) % buttons.length;
        else if (key === "Home") next = 0;
        else if (key === "End") next = buttons.length - 1;
        else if (key === " " || key === "Enter") {
          event.preventDefault();
          setMode(doc, storage, media, btn.getAttribute("data-theme-choice"));
          return;
        } else return;
        event.preventDefault();
        buttons[next].focus();
        setMode(doc, storage, media, buttons[next].getAttribute("data-theme-choice"));
      });
    });
  }

  var api = {
    KEY: KEY,
    resolveTheme: resolveTheme,
    readMode: readMode,
    writeMode: writeMode,
    apply: apply,
    boot: boot,
    bindToggle: bindToggle,
    syncToggle: syncToggle,
    setMode: setMode,
  };
  global.EnactTheme = api;

  if (global.document && global.document.documentElement) {
    var media = currentMedia();
    try {
      boot(global.document, global.localStorage, media);
    } catch (err) {}
    function attach() {
      try {
        bindToggle(global.document, global.localStorage, currentMedia());
      } catch (err) {}
    }
    if (global.document.readyState === "loading") {
      global.document.addEventListener("DOMContentLoaded", attach);
    } else {
      attach();
    }
    function followSystem() {
      if (readMode(global.localStorage) === "system") {
        apply(global.document, "system", currentMedia().matches);
        syncToggle(global.document, "system");
      }
    }
    if (media && media.addEventListener) {
      media.addEventListener("change", followSystem);
    } else if (media && media.addListener) {
      media.addListener(followSystem);
    }
    if (global.addEventListener) {
      global.addEventListener("storage", function (event) {
        if (!event.key || event.key === KEY) {
          boot(global.document, global.localStorage, currentMedia());
        }
      });
    }
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
