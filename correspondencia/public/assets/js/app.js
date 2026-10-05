(function () {
  'use strict';
  var $ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  // Filtro instantáneo de listas/tablas
  $('[data-filtro]').forEach(function (inp) {
    inp.addEventListener('input', function () {
      var q = inp.value.toLowerCase();
      $(inp.getAttribute('data-filtro')).forEach(function (el) { el.style.display = el.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none'; });
    });
  });

  // Seleccionar todo
  $('[data-todos]').forEach(function (cb) {
    cb.addEventListener('change', function () {
      $(cb.getAttribute('data-todos')).forEach(function (c) { if (c.closest('.item').style.display !== 'none') c.checked = cb.checked; });
    });
  });

  // Confirmaciones
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-confirm]');
    if (t && !window.confirm(t.getAttribute('data-confirm'))) e.preventDefault();
    var p = e.target.closest('[data-print]');
    if (p) { e.preventDefault(); window.print(); }
  });

  // Rellenar destinatario / vía desde el selector de funcionarios
  $('select[data-fill]').forEach(function (sel) {
    sel.addEventListener('change', function () {
      var o = sel.options[sel.selectedIndex], f = sel.getAttribute('data-fill'), form = sel.form;
      if (!o || !o.getAttribute('data-nombre')) return;
      form.elements[f + '_nombre'].value = o.getAttribute('data-nombre');
      form.elements[f + '_cargo'].value = o.getAttribute('data-cargo');
    });
  });

  // Autocompletado de NUR propios
  $('[data-nur]').forEach(function (inp) {
    var dl = document.getElementById('nurs'), t;
    inp.addEventListener('input', function () {
      clearTimeout(t);
      t = setTimeout(function () {
        if (inp.value.length < 2) return;
        fetch(window.URL_HOJAS + '&q=' + encodeURIComponent(inp.value), { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (rows) {
          dl.innerHTML = '';
          rows.forEach(function (r) { var o = document.createElement('option'); o.value = r.nur; o.label = r.referencia; dl.appendChild(o); });
        }).catch(function () {});
      }, 250);
    });
  });

  // Editor enriquecido (si Quill carga; si no, queda el textarea)
  window.addEventListener('load', function () {
    var form = document.querySelector('[data-editor-form]');
    if (form && window.Quill) {
      var ta = document.getElementById('contenido'), ed = document.getElementById('editor');
      ed.style.display = 'block'; ta.style.display = 'none';
      var q = new Quill(ed, { theme: 'snow', modules: { toolbar: [[{ header: [1, 2, 3, false] }], ['bold', 'italic', 'underline'], [{ list: 'ordered' }, { list: 'bullet' }], [{ align: [] }], ['link'], ['clean']] } });
      q.clipboard.dangerouslyPasteHTML(ta.value);
      form.addEventListener('submit', function () { ta.value = q.getText().trim() === '' ? '' : q.root.innerHTML; });
    }
    // Gráficos
    if (window.Chart) {
      var colores = ['#2b6cb0', '#c0392b', '#2f9e44'];
      $('canvas[data-chart]').forEach(function (c) {
        var d = JSON.parse(c.getAttribute('data-chart'));
        d.datasets.forEach(function (s, i) { s.backgroundColor = colores[i % 3]; });
        new Chart(c, { type: 'bar', data: d, options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } });
      });
    }
  });
})();
