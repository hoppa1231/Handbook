import dotenv from 'dotenv';

dotenv.config();

const DEFAULT_DB_URL = 'postgres://postgres:postgres@db:5432/handbook';

const environment = {
  nodeEnv: process.env.NODE_ENV ?? 'development',
  port: Number.parseInt(
    process.env.PORT_BACKEND ?? process.env.PORT ?? '3000',
    10
  ),
  databaseUrl: process.env.DATABASE_URL ?? DEFAULT_DB_URL
};

export default environment;
