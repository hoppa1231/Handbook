import { PoolClient } from 'pg';
import { pool } from './pool';

const schemaStatements: string[] = [
  `create table if not exists request_types (
    code text primary key,
    description text not null
  )`,
  `create table if not exists request_statuses (
    code text primary key,
    description text not null
  )`,
  `create table if not exists product_categories (
    code text primary key,
    description text not null
  )`,
  `create table if not exists suppliers (
    id serial primary key,
    name varchar(100) not null,
    address varchar(200),
    contact varchar(100),
    website varchar(100),
    rating double precision
  )`,
  `create table if not exists products (
    id serial primary key,
    part_number varchar(100) not null,
    name varchar(100) not null,
    brand varchar(100),
    model varchar(100),
    serial_number integer,
    scheme varchar(50),
    pos_scheme varchar(100),
    material varchar(50),
    size varchar(50),
    comment varchar(300),
    category text references product_categories(code)
  )`,
  `create table if not exists requests (
    id serial primary key,
    id_request integer not null unique,
    type_request text references request_types(code),
    datetime_coming timestamptz not null,
    datetime_delivery timestamptz,
    status text references request_statuses(code),
    total_price double precision
  )`,
  `create table if not exists supplier_product_prices (
    id serial primary key,
    product_id integer not null references products(id) on delete cascade,
    supplier_id integer not null references suppliers(id) on delete cascade,
    total_price double precision,
    lead_time interval,
    cy double precision,
    constraint supplier_product_unique unique (product_id, supplier_id)
  )`,
  `create table if not exists request_items (
    id serial primary key,
    part_number varchar(100),
    name varchar(100) not null,
    quantity integer,
    unit varchar(20),
    brand varchar(100),
    model varchar(100),
    serial_number integer,
    scheme varchar(50),
    pos_scheme varchar(100),
    material varchar(50),
    comment varchar(300),
    unit_price double precision,
    total_price double precision,
    request_id integer references requests(id) on delete cascade,
    product_id integer references products(id) on delete set null
  )`
];

const migrationStatements: string[] = [
  `alter table if exists products
     alter column part_number type varchar(100) using part_number::text,
     alter column pos_scheme type varchar(100) using pos_scheme::text`,
  `alter table if exists request_items
     alter column part_number type varchar(100) using part_number::text,
     alter column pos_scheme type varchar(100) using pos_scheme::text`
];

const seedStatements: string[] = [
  `insert into request_types (code, description) values
    ('exam', 'Market survey'),
    ('info', 'Data lookup'),
    ('work', 'Operational request')
   on conflict (code) do update set description = excluded.description`,
  `insert into request_statuses (code, description) values
    ('new', 'New request'),
    ('in_progress', 'In progress'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled')
   on conflict (code) do update set description = excluded.description`,
  `insert into product_categories (code, description) values
    ('wall', 'Wall'),
    ('valve', 'Valve'),
    ('frame', 'Frame')
   on conflict (code) do update set description = excluded.description`
];

const runStatements = async (client: PoolClient, statements: string[]) => {
  for (const statement of statements) {
    await client.query(statement);
  }
};

export const initializeDatabase = async (): Promise<void> => {
  const client = await pool.connect();
  try {
    await client.query('begin');
    await runStatements(client, schemaStatements);
    await runStatements(client, migrationStatements);
    await runStatements(client, seedStatements);
    await client.query('commit');
  } catch (error) {
    await client.query('rollback');
    throw error;
  } finally {
    client.release();
  }
};
