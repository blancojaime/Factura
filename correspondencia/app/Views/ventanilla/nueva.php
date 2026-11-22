<div class="vent-head"><div><h2>Ventanilla Única</h2><p>Recepción de correspondencia externa</p></div><span class="vent-chip">Registro oficial</span></div>
<form method="post" enctype="multipart/form-data" class="form vent-form"><?= csrf_field() ?>
  <p class="muted">Registre el documento recibido de un ciudadano, comunidad o institución. Se genera el NUR, se deriva al funcionario elegido y se imprimen el <b>cargo</b>, las <b>etiquetas</b> y, si lo desea, el <b>sello QR</b> sobre la copia de la nota.</p>
  <fieldset class="vent-sec s1"><legend><i>1</i> Datos del remitente</legend>
    <div class="cols"><label>Remitente (persona o comunidad)<input name="remitente" required maxlength="150"></label><label>Institución / OTB (opcional)<input name="institucion" maxlength="150"></label></div>
    <label>Celular de contacto<input name="celular" maxlength="30" inputmode="tel"></label></fieldset>
  <fieldset class="vent-sec s2"><legend><i>2</i> Documento presentado</legend>
    <div class="cols"><label>Tipo de entrada (carta, solicitud, informe…)<input name="documento" list="tipos_entrada" maxlength="120" required><datalist id="tipos_entrada"><option>Carta</option><option>Solicitud</option><option>Informe</option><option>Nota</option><option>Oficio</option><option>Invitación</option><option>Denuncia</option><option>Reclamo</option></datalist></label><label>Nº de fojas<input name="fojas" maxlength="30"></label></div>
    <div class="cols"><label>Anexos (ej. 1 folder, 1 CD)<input name="anexos" maxlength="80"></label><label>Escaneo / fotografía (opcional)<input type="file" name="archivos[]" multiple></label></div>
    <label>Referencia / asunto<input name="referencia" required maxlength="255"></label></fieldset>
  <fieldset class="vent-sec s3"><legend><i>3</i> Derivación</legend>
    <label>Derivar a <?= select_usuarios('destino', 0, 'required') ?></label>
    <label>Proveído<input name="proveido" maxlength="255" placeholder="Correspondencia externa recibida en ventanilla"></label>
    <label class="radio"><input type="checkbox" name="urgente" value="1"> Marcar como <b>urgente</b></label></fieldset>
  <fieldset class="vent-sec s4"><legend><i>4</i> Observaciones</legend><label>Observaciones<textarea name="observaciones" rows="3"></textarea></label></fieldset>
  <button class="btn primary vent-btn">Registrar y derivar</button></form>
