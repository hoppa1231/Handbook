FROM node:20-alpine AS build

WORKDIR /app

COPY backend/package*.json ./
RUN npm install

COPY backend/tsconfig.json ./
COPY backend/src ./src
COPY openapi ./openapi

RUN npm run build

FROM node:20-alpine AS runtime

WORKDIR /app

ARG PORT_BACKEND=3000
ENV NODE_ENV=production \
    PORT_BACKEND=${PORT_BACKEND}

COPY backend/package*.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/openapi ./openapi

EXPOSE ${PORT_BACKEND}

CMD ["node", "dist/server.js"]
