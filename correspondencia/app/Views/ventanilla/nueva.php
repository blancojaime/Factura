<form method="post" enctype="multipart/form-data" class="form card"><?= csrf_field() ?>
  <p class="muted">Registre el documento recibido de un ciudadano, comunidad o institución. Se genera el NUR, se deriva al funcionario elegido y se imprime el cargo de recepción.</p>
  <div class="cols"><label>Remitente (persona o comunidad)<input name="remitente" required maxlength="150"></label><label>Institución / OTB (opcional)<input name="institucion" maxlength="150"></label></div>
  <div class="cols"><label>Documento presentado (carta, solicitud…)<input name="documento" maxlength="120"></label><label>Nº de fojas<input name="fojas" maxlength="30"></label></div>
  <label>Referencia / asunto<input name="referencia" required maxlength="255"></label>
  <label>Derivar a <?= select_usuarios('destino', 0, 'required') ?></label>
  <label>Proveído<input name="proveido" maxlength="255" placeholder="Correspondencia externa recibida en ventanilla"></label>
  <label>Observaciones<textarea name="observaciones" rows="3"></textarea></label>
  <label>Escaneo / fotografía del documento (opcional)<input type="file" name="archivos[]" multiple></label>
  <label class="radio"><input type="checkbox" name="urgente" value="1"> Urgente</label>
  <button class="btn primary">Registrar y derivar</button></form>
