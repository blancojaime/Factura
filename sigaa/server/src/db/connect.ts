import knex, { Knex } from 'knex';
import pg from 'pg';
import fs from 'node:fs';
import path from 'node:path';

// PostgreSQL devuelve date/numeric como objetos/cadenas; los normalizamos como en SQLite.
pg.types.setTypeParser(1082, (v: string) => v); // date
pg.types.setTypeParser(1114, (v: string) => v); // timestamp
pg.types.setTypeParser(1700, (v: string) => parseFloat(v)); // numeric
pg.types.setTypeParser(20, (v: string) => parseInt(v, 10)); // bigint

export interface DbOptions {
  /** postgres://user:pass@host:5432/db  |  sqlite:./data/sigaa.sqlite  |  sqlite::memory: */
  url?: string;
}

export function connect(opts: DbOptions = {}): Knex {
  const url = opts.url || process.env.DATABASE_URL || 'sqlite:./data/sigaa.sqlite';
  if (url.startsWith('postgres')) {
    return knex({ client: 'pg', connection: url, pool: { min: 0, max: 10 } });
  }
  const file = url.replace(/^sqlite:/, '');
  const conn = file === ':memory:' || file === '' ? ':memory:' : file;
  if (conn !== ':memory:') fs.mkdirSync(path.dirname(path.resolve(conn)), { recursive: true });
  return knex({
    client: 'better-sqlite3',
    connection: { filename: conn },
    useNullAsDefault: true,
    pool: {
      min: 1,
      max: 1,
      afterCreate: (c: any, done: (e: Error | null, c: any) => void) => {
        c.pragma('journal_mode = WAL');
        c.pragma('foreign_keys = ON');
        done(null, c);
      },
    },
  });
}

export const isPg = (db: Knex): boolean => String((db.client as any).config?.client || '').includes('pg');
