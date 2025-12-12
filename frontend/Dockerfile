# ========================================
# Stage 1: Build
# ========================================
FROM node:20-alpine as build

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar código fuente
COPY . .

# ⚠️ CRÍTICO: Recibir variable de Railway
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Log para debug (opcional)
RUN echo "Building with VITE_API_URL=${VITE_API_URL}"

# Build de producción
RUN npm run build

# ========================================
# Stage 2: Production con Nginx
# ========================================
FROM nginx:alpine

# Copiar el build
COPY --from=build /app/dist /usr/share/nginx/html

# Copiar configuración nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]