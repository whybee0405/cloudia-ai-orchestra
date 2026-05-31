FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY cloudia-ai-frontend/package*.json ./
RUN npm ci
COPY cloudia-ai-frontend/ ./
RUN npm run build

FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /app/dist /usr/share/nginx/html
COPY nginx/cloudia.conf.template /etc/nginx/templates/cloudia.conf.template
EXPOSE 80
