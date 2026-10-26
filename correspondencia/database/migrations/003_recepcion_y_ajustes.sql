-- Hoja de ruta con QR, ventanilla (anexos/celular) y datos de la entidad (logo).
ALTER TABLE hojas_ruta ADD COLUMN ext_anexos VARCHAR(80) NULL AFTER ext_documento;
ALTER TABLE hojas_ruta ADD COLUMN ext_celular VARCHAR(30) NULL AFTER ext_anexos;
CREATE TABLE IF NOT EXISTS ajustes (
  clave VARCHAR(60) NOT NULL PRIMARY KEY,
  valor TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
