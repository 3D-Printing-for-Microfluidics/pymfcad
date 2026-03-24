(function () {
  function getColorScheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function renderDiffBlocks() {
    var wrappers = document.querySelectorAll('.diff2html-wrapper');
    if (!wrappers.length || !window.Diff2Html) return;

    console.log(wrappers);
    wrappers.forEach(function (wrapper) {
      var target = wrapper.querySelector('.diff2html');
      var source = wrapper.querySelector('.diff2html-source');
      if (!target || !source) return;

      var diff = source.textContent || '';
      // Preserve empty context lines so diff2html doesn't drop them
      diff = diff.replace(/^\s*$/gm, ' ');
      if (!diff.trim()) return;

      var html = window.Diff2Html.html(diff, {
        drawFileList: false,
        matching: 'none',
        matchWordsThreshold: 0,
        matchingMaxComparisons: 0,
        diffStyle: 'line',
        colorScheme: getColorScheme(),
        outputFormat: 'line-by-line',
        highlight: true
      });

      target.innerHTML = html;

      function highlightIdentifiers(root, identifiersByType) {
        if (!identifiersByType) return;

        var classMap = {};
        function addToMap(list, className) {
          if (!list || !list.length) return;
          list.forEach(function (name) {
            if (!classMap[name]) {
              classMap[name] = className;
            }
          });
        }

        addToMap(identifiersByType.classes || [], 'd2h-id-class');
        addToMap(identifiersByType.functions || [], 'd2h-id-function');
        addToMap(identifiersByType.imports || [], 'd2h-id-import');
        addToMap(identifiersByType.variables || [], 'd2h-id-variable');

        var identifiers = Object.keys(classMap);
        if (!identifiers.length) return;

        var escaped = identifiers.map(function (id) {
          return id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        });
        var pattern = new RegExp('\\b(' + escaped.join('|') + ')\\b', 'g');

        function hasHighlightAncestor(node) {
          var el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
          if (!el) return false;
          return !!el.closest(
            '.hljs-comment, .hljs-quote, .hljs-string, .d2h-id-class, .d2h-id-function, .d2h-id-variable, .d2h-id-import'
          );
        }

        function walk(node) {
          if (node.nodeType === Node.TEXT_NODE) {
            if (hasHighlightAncestor(node)) return;
            var text = node.nodeValue;
            if (!text || !pattern.test(text)) return;
            var frag = document.createDocumentFragment();
            var lastIndex = 0;
            text.replace(pattern, function (match, _group, offset) {
              if (offset > lastIndex) {
                frag.appendChild(document.createTextNode(text.slice(lastIndex, offset)));
              }
              var span = document.createElement('span');
              span.className = classMap[match] || 'd2h-id-variable';
              span.textContent = match;
              frag.appendChild(span);
              lastIndex = offset + match.length;
            });
            if (lastIndex < text.length) {
              frag.appendChild(document.createTextNode(text.slice(lastIndex)));
            }
            node.parentNode.replaceChild(frag, node);
            return;
          }

          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'SCRIPT' || node.tagName === 'STYLE') return;
            Array.prototype.forEach.call(node.childNodes, walk);
          }
        }

        walk(root);
      }

      if (window.hljs) {
        var codeLines = target.querySelectorAll('.d2h-code-line-ctn');
        codeLines.forEach(function (line) {
          var text = line.textContent || '';
          if (!text.trim()) return;
          try {
            var highlighted = window.hljs.highlight(text, { language: 'python' }).value;
            line.innerHTML = highlighted;
          } catch (e) {
            // Fallback to auto-detect if Python highlighting fails
            try {
              var autoHighlighted = window.hljs.highlightAuto(text).value;
              line.innerHTML = autoHighlighted;
            } catch (err) {
              // leave as-is
            }
          }

          highlightIdentifiers(line, window.DIFF2HTML_PY_IDENTIFIERS || {});
        });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderDiffBlocks);
  } else {
    renderDiffBlocks();
  }

  window.addEventListener('themechange', function () {
    renderDiffBlocks();
  });
})();
