import { Pool } from 'pg';
import environment from '../config/environment';

export const pool = new Pool({
  connectionString: environment.databaseUrl
});

export const verifyConnection = async (): Promise<void> => {
  await pool.query('select 1');
};

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const waitForConnection = async (
  attempts = 10,
  intervalMs = 1000
): Promise<void> => {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      await verifyConnection();
      if (attempt > 1) {
        console.log(`Database connection established on attempt ${attempt}`);
      }
      return;
    } catch (error) {
      if (attempt === attempts) {
        throw error;
      }
      console.log(
        `Database not ready (attempt ${attempt} of ${attempts}). Retrying in ${intervalMs}ms...`
      );
      await delay(intervalMs);
    }
  }
};
