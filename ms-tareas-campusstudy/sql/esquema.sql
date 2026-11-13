-- Base de datos propia del servicio de Tareas (CampusStudy, Grupo #1)
-- No contiene datos de usuarios, materias ni grupos: solo sus identificadores.

CREATE DATABASE IF NOT EXISTS campusstudy_tareas
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE campusstudy_tareas;

CREATE TABLE IF NOT EXISTS tareas (
  tarea_id            INT AUTO_INCREMENT PRIMARY KEY,
  titulo              VARCHAR(150)  NOT NULL,
  descripcion         TEXT          NULL,
  usuario_id          INT           NOT NULL,
  materia_id          INT           NOT NULL,
  grupo_id            INT           NULL,
  fecha_entrega       DATE          NOT NULL,
  hora_entrega        VARCHAR(5)    NULL,
  prioridad           VARCHAR(10)   NOT NULL DEFAULT 'media',
  estado              VARCHAR(15)   NOT NULL DEFAULT 'pendiente',
  fecha_creacion      DATETIME      NOT NULL,
  fecha_actualizacion DATETIME      NOT NULL,
  INDEX idx_usuario (usuario_id),
  INDEX idx_materia (materia_id),
  INDEX idx_grupo (grupo_id),
  INDEX idx_estado (estado),
  INDEX idx_entrega (fecha_entrega),
  CONSTRAINT chk_prioridad CHECK (prioridad IN ('baja','media','alta')),
  CONSTRAINT chk_estado CHECK (estado IN ('pendiente','en_progreso','completada','cancelada'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Eventos que no se pudieron entregar a Notificaciones (sección J del contrato)
CREATE TABLE IF NOT EXISTS eventos_pendientes (
  evento_id      INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id     INT          NOT NULL,
  tipo           VARCHAR(30)  NOT NULL,
  referencia_id  INT          NOT NULL,
  mensaje        VARCHAR(300) NOT NULL,
  fecha_evento   DATETIME     NOT NULL,
  intentos       INT          NOT NULL DEFAULT 1,
  ultimo_intento DATETIME     NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Claves de idempotencia: si el Front reintenta una creación porque no le llegó
-- la respuesta, se devuelve la tarea ya creada en lugar de duplicarla.
CREATE TABLE IF NOT EXISTS peticiones_idempotentes (
  clave          VARCHAR(80) PRIMARY KEY,
  tarea_id       INT      NOT NULL,
  fecha_creacion DATETIME NOT NULL,
  INDEX idx_fecha (fecha_creacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
