<form method="post" enctype="multipart/form-data" class="form card"><?= csrf_field() ?>
  <p class="muted">Registre el documento recibido de un ciudadano, comunidad o institución. Se genera el NUR, se deriva al funcionario elegido y se imprimen la <b>etiqueta</b> (logo, código y QR) y el <b>cargo de recepción</b>.</p>
  <div class="cols"><label>Remitente (persona o comunidad)<input name="remitente" required maxlength="150"></label><label>Institución / OTB (opcional)<input name="institucion" maxlength="150"></label></div>
  <div class="cols"><label>Tipo de entrada (carta, solicitud, informe…)<input name="documento" list="tipos_entrada" maxlength="120" required><datalist id="tipos_entrada"><option>Carta</option><option>Solicitud</option><option>Informe</option><option>Nota</option><option>Oficio</option><option>Invitación</option><option>Denuncia</option><option>Reclamo</option></datalist></label><label>Nº de fojas<input name="fojas" maxlength="30"></label></div>
  <div class="cols"><label>Anexos (ej. 1 folder, 1 CD)<input name="anexos" maxlength="80"></label><label>Celular de contacto<input name="celular" maxlength="30" inputmode="tel"></label></div>
  <label>Referencia / asunto<input name="referencia" required maxlength="255"></label>
  <label>Derivar a <?= select_usuarios('destino', 0, 'required') ?></label>
  <label>Proveído<input name="proveido" maxlength="255" placeholder="Correspondencia externa recibida en ventanilla"></label>
  <label>Observaciones<textarea name="observaciones" rows="3"></textarea></label>
  <label>Escaneo / fotografía del documento (opcional)<input type="file" name="archivos[]" multiple></label>
  <label class="radio"><input type="checkbox" name="urgente" value="1"> Urgente</label>
  <button class="btn primary">Registrar y derivar</button></form>
