-- Para bases ya instaladas con la versión anterior:
ALTER TABLE usuarios ADD COLUMN cambiar_clave TINYINT(1) NOT NULL DEFAULT 0 AFTER activo;
