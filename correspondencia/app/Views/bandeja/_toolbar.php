<div class="toolbar">
  <label>Filtrar: <input type="search" data-filtro=".item" placeholder="NUR, referencia, remitente…"></label>
  <span>Ordenar por:
    <?php foreach (['hr' => 'Hoja Ruta', 'fecha' => 'Fecha', 'oficina' => 'Oficina', 'proceso' => 'Proceso'] as $k => $t): ?>
      <a href="<?= url($_GET['r'], array_filter(['orden' => $k, 'mostrar' => $_GET['mostrar'] ?? null])) ?>" class="<?= ($orden ?? '') === $k ? 'on' : '' ?>"><?= $t ?></a>
    <?php endforeach; ?></span>
  <label><input type="checkbox" data-todos=".item input[type=checkbox]"> Seleccionar todo</label>
</div>
