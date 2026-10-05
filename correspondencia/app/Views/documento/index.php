<?php $hoja = (int)($hoja ?? 0); ?>
<p class="muted"><?= $hoja ? 'Elija el tipo de documento de respuesta (se enlazará al mismo NUR).' : 'Elija el tipo de documento a crear. Algunos tipos pueden estar deshabilitados para su oficina.' ?></p>
<div class="tipos"><?php foreach ($tipos as $t): ?>
  <a class="tipo" href="<?= url('documento/nuevo', ['tipo' => $t['id']] + ($hoja ? ['hoja' => $hoja] : [])) ?>"><b><?= e($t['nombre']) ?></b><small><?= e($t['prefijo']) ?>/<?= e(App\Core\Config::get('entidad_sigla')) ?>/<?= e(App\Core\Auth::user()['oficina_sigla']) ?> Nº …/<?= gestion() ?></small></a><?php endforeach; ?></div>
