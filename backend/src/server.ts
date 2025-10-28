import app from './app';
import environment from './config/environment';
import { waitForConnection } from './db/pool';
import { initializeDatabase } from './db/schema';

const start = async () => {
  try {
    console.log('Waiting for database connection...');
    await waitForConnection();
    await initializeDatabase();

    app.listen(environment.port, () => {
      console.log(
        `Server is listening on port ${environment.port} in ${environment.nodeEnv} mode`
      );
    });
  } catch (error) {
    console.error('Failed to start the server', error);
    process.exit(1);
  }
};

void start();
