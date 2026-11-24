document.querySelectorAll('.filter').forEach(function (inp) {
  inp.addEventListener('input', function () {
    var q = inp.value.trim().toLowerCase();
    var scope = document.querySelector(inp.dataset.target);
    if (!scope) return;
    scope.querySelectorAll('.tile, tbody tr').forEach(function (el) {
      var t = (el.dataset.name || el.textContent).toLowerCase();
      el.style.display = !q || t.indexOf(q) >= 0 ? '' : 'none';
    });
    scope.querySelectorAll('h3').forEach(function (h) {
      var g = h.nextElementSibling;
      if (!g) return;
      var any = Array.prototype.some.call(g.children, function (c) { return c.style.display !== 'none'; });
      h.style.display = any ? '' : 'none';
      g.style.display = any ? '' : 'none';
    });
  });
});
