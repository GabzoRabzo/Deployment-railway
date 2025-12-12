# ========================================
# Etapa 1: Build
# ========================================
FROM node:20-alpine AS build

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar TODAS las dependencias (incluyendo devDependencies)
RUN npm ci

# Copiar código fuente
COPY . .

# Build de producción
RUN npm run build

# ========================================
# Etapa 2: Producción con Nginx
# ========================================
FROM nginx:alpine

# Copiar build desde la etapa anterior
COPY --from=build /app/dist /usr/share/nginx/html

# Copiar configuración de nginx (si la tienes)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]