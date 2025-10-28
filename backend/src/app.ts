import fs from 'node:fs';
import fsPromises from 'node:fs/promises';
import path from 'node:path';
import express, { Request, Response, NextFunction } from 'express';
import routes from './routes';

const resolveOpenApiPath = (): string | undefined => {
  const candidates = [
    path.resolve(process.cwd(), 'openapi', 'openapi.json'),
    path.resolve(process.cwd(), '..', 'openapi', 'openapi.json')
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  console.warn('OpenAPI specification file not found. Swagger docs will be unavailable.');
  return undefined;
};

const swaggerHtml = `
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Handbook API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; }
      #swagger-ui { height: 100vh; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: '/api/openapi.json',
          dom_id: '#swagger-ui'
        });
      };
    </script>
  </body>
</html>
`;

const app = express();

app.use(express.json());

const openApiPath = resolveOpenApiPath();

app.get('/api/openapi.json', async (_req, res, next) => {
  if (!openApiPath) {
    res.status(404).json({ message: 'OpenAPI specification not found' });
    return;
  }

  try {
    const raw = await fsPromises.readFile(openApiPath, 'utf-8');
    res.type('application/json').send(raw);
  } catch (error) {
    next(error);
  }
});

app.get('/api/docs', (_req, res) => {
  if (!openApiPath) {
    res
      .status(503)
      .json({ message: 'OpenAPI specification not found. Documentation is unavailable.' });
    return;
  }

  res.type('text/html').send(swaggerHtml);
});

app.use('/api', routes);

app.use((req, res) => {
  res.status(404).json({ message: 'Resource not found', path: req.path });
});

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  // Centralized error handler keeps the surface area small for now.
  res.status(500).json({ message: err.message ?? 'Internal server error' });
});

export default app;
