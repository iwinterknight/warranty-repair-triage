# Frontend image — multi-stage: Vite build → static nginx. The browser (on the host) calls the backend
# at localhost:8000, which is the compose-mapped port, so the default VITE_API_URL is already correct.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
