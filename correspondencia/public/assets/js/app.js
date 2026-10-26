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
        fetch(window.URL_HOJAS + '&q=' + encodeURIComponent(inp.value) + (inp.getAttribute('data-todas') ? '&todas=1' : ''), { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (rows) {
          dl.innerHTML = '';
          rows.forEach(function (r) { var o = document.createElement('option'); o.value = r.nur; o.label = r.referencia; dl.appendChild(o); });
        }).catch(function () {});
      }, 250);
    });
  });

  // Códigos QR (se dibujan en el navegador, sin internet)
  if (window.qrcode) {
    $('[data-qr]').forEach(function (el) {
      try { var q = qrcode(0, 'M'); q.addData(el.getAttribute('data-qr')); q.make(); el.innerHTML = q.createSvgTag({ scalable: true, margin: 0 }); }
      catch (e) { el.textContent = 'QR no disponible'; }
    });
  }

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
    // Gráficos (Chart.js si está disponible; si no, un dibujo propio sin internet)
    function barras(c, d) {
      var H = Math.max(parseInt(c.getAttribute('height'), 10) || 200, 230), W = c.parentNode.clientWidth || 600;
      c.width = W; c.height = H; c.style.width = '100%';
      var x = c.getContext('2d'), col = ['#2b6cb0', '#c0392b', '#2f9e44'], n = d.labels.length, m = d.datasets.length, top = 10, bot = 70, left = 30;
      var max = 1; d.datasets.forEach(function (s) { s.data.forEach(function (v) { if (v > max) max = v; }); });
      var gw = (W - left - 10) / Math.max(n, 1), bw = Math.min(26, (gw - 8) / m);
      x.font = '11px sans-serif'; x.fillStyle = '#6b7785'; x.strokeStyle = '#d5dce6';
      var st = Math.min(4, max); for (var g = 0; g <= st; g++) { var yy = top + (H - top - bot) * (1 - g / st); x.beginPath(); x.moveTo(left, yy); x.lineTo(W - 5, yy); x.stroke(); x.fillText(String(Math.round(max * g / st)), 4, yy + 4); }
      d.labels.forEach(function (lb, i) {
        d.datasets.forEach(function (s, j) {
          var h = (H - top - bot) * (s.data[i] / max), bx = left + i * gw + (gw - bw * m) / 2 + j * bw;
          x.fillStyle = col[j % 3]; x.fillRect(bx, H - bot - h, bw - 2, h);
        });
        x.save(); x.translate(left + i * gw + gw / 2, H - bot + 8); x.rotate(-0.6); x.fillStyle = '#1d2733'; x.textAlign = 'right'; x.fillText(String(lb).slice(0, 14), 0, 4); x.restore();
      });
      d.datasets.forEach(function (s, j) { var lx = left + j * Math.max(95, (W - left) / m); x.fillStyle = col[j % 3]; x.fillRect(lx, H - 14, 10, 10); x.fillStyle = '#1d2733'; x.font = '10px sans-serif'; x.fillText(s.label.replace('Pendientes oficiales', 'Pend. oficiales').replace('Copias pendientes', 'Copias pend.'), lx + 14, H - 5); });
    }
    if (!window.Chart) { $('canvas[data-chart]').forEach(function (c) { barras(c, JSON.parse(c.getAttribute('data-chart'))); }); }
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
