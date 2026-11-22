<?php
// Nombres de ejemplo para la demo (clave Demo12345). Uso: php tools/manuales/seed.php
require dirname(__DIR__, 2) . '/app/bootstrap.php';
use App\Core\DB;
$n = ['u401'=>['Ana Mamani Quispe','AM'],'u402'=>['Beto Flores Rojas','BF'],'u410'=>['Carla Choque Apaza','CC'],'u411'=>['Rosa Quispe Vela','RQ'],'u404'=>['Luis Rojas Condori','LR'],'u407'=>['Pedro Condori Ticona','PC'],'u403'=>['Elena Vargas Mamani','EV'],'u435'=>['Dani Torrez Lima','DT'],'u426'=>['Patricia Ticona Rios','PT'],'u405'=>['Mario Callisaya Pari','MC'],'u406'=>['Jorge Apaza Luna','JA'],'u432'=>['Rubén Choque Pari','RC']];
foreach ($n as $l => [$nom,$m]) DB::exec("UPDATE usuarios SET nombre=?, mosca=?, password_hash=?, cambiar_clave=0 WHERE login=?", [$nom,$m,password_hash('Demo12345', PASSWORD_DEFAULT),$l]);
echo "ok\n";
