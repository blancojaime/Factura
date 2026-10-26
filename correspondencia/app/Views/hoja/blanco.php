<div class="card">
  <p>Imprima la <b>hoja de ruta de un trámite</b> con la cabecera completa (datos del trámite y <b>código QR</b>) y las <b>hojas anexas</b> que necesite, para registrar manualmente los movimientos. Cada anexa lleva en la parte superior el CITE y el número del trámite.</p>
  <form method="get" action="<?= url() ?>" class="form" target="_blank"><input type="hidden" name="r" value="hoja/imprimir">
    <label>Número del trámite (NUR)<input name="nur" list="nurs" data-nur data-todas="1" autocomplete="off" required value="<?= e($nur) ?>" placeholder="<?= e(App\Core\Config::get('entidad_sigla')) ?>/<?= gestion() ?>-00001"><datalist id="nurs"></datalist></label>
    <div class="cols">
      <label>Contenido de los bloques<select name="modo"><option value="blanco" <?= $modo === 'blanco' ? 'selected' : '' ?>>En blanco (para llenar a mano)</option><option value="registrado" <?= $modo === 'registrado' ? 'selected' : '' ?>>Con las derivaciones ya registradas</option></select></label>
      <label>Hojas anexas (0 a 20)<input type="number" name="anexas" min="0" max="20" value="<?= e($anexas) ?>"></label>
    </div>
    <button class="btn primary">Ver e imprimir</button>
  </form>
  <p class="muted">Tamaño <b>Carta, vertical</b>. La primera hoja trae 3 bloques de derivación y cada anexa 4. Al abrir, también puede cambiar la cantidad de anexas antes de imprimir.</p>
</div>
