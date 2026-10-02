/** Error de regla de negocio: se devuelve al usuario con HTTP 422 y su mensaje. */
export class BusinessError extends Error {
  status = 422;
  constructor(message: string) {
    super(message);
    this.name = 'BusinessError';
  }
}
export class NotFound extends BusinessError {
  constructor(message: string) {
    super(message);
    this.status = 404;
  }
}
export class Forbidden extends BusinessError {
  constructor(message = 'No tiene permiso para esta acción.') {
    super(message);
    this.status = 403;
  }
}
/** Lanza BusinessError con el texto dado. */
export function fail(msg: string): never {
  throw new BusinessError(msg);
}
/** Acumula errores de validación y los lanza juntos (como las listas "- ..." del sistema original). */
export class Errores {
  private list: string[] = [];
  add(cond: unknown, msg: string) {
    if (cond) this.list.push(msg);
  }
  get any() {
    return this.list.length > 0;
  }
  get items() {
    return [...this.list];
  }
  throwIfAny(prefix = 'No se puede continuar:') {
    if (this.list.length) fail(`${prefix}\n${this.list.map((m) => '- ' + m).join('\n')}`);
  }
}
