<?php $hoja = (int)($hoja ?? 0); $u = App\Core\Auth::user(); ?>
<p class="muted"><?= $hoja ? 'Elija el tipo de documento de respuesta (se enlazará al mismo NUR).' : 'Elija el tipo de documento a crear. Cada tipo tiene su color para reconocerlo fácilmente.' ?></p>
<div class="tipos-vivos"><?php foreach ($tipos as $t): $est = tipo_estilo($t['prefijo']); ?>
  <a class="tipo-card" style="--tc:<?= e($est['color']) ?>" href="<?= url('documento/nuevo', ['tipo' => $t['id']] + ($hoja ? ['hoja' => $hoja] : [])) ?>">
    <span class="tc-top"><i><?= e($t['prefijo']) ?></i></span>
    <span class="tc-cuerpo"><b><?= e($t['nombre']) ?></b><em><?= e($est['desc']) ?></em>
      <small><?= e($t['prefijo']) ?>/<?= e(App\Core\Config::get('entidad_sigla')) ?>/<?= e($u['oficina_sigla']) ?> Nº 0001/<?= gestion() ?></small></span>
  </a><?php endforeach; ?></div>
