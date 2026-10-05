<section class="card"><p><b>Usuario:</b> <?= e($u['login']) ?><br><b>Oficina:</b> <?= e($u['oficina']) ?><br><b>Nombre:</b> <?= e($u['nombre']) ?><br><b>Cargo:</b> <?= e($u['cargo']) ?><br><b>Correo:</b> <?= e($u['email']) ?><br>
<b>Último ingreso:</b> <?= e(fecha_corta($u['ultimo_ingreso'])) ?><br><b>Número de ingresos:</b> <?= (int)$u['nro_ingresos'] ?></p></section>
