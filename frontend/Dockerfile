# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- serve stage ----
FROM nginx:1.27-alpine
# This .envsh is *sourced* by the image's docker-entrypoint (before the
# 20-envsubst step) and exports ${NGINX_LOCAL_RESOLVERS} from /etc/resolv.conf.
# sed strips any CRLF picked up on Windows checkouts; chmod makes it sourceable.
COPY 15-local-resolvers.envsh /docker-entrypoint.d/15-local-resolvers.envsh
RUN sed -i 's/\r$//' /docker-entrypoint.d/15-local-resolvers.envsh \
    && chmod +x /docker-entrypoint.d/15-local-resolvers.envsh
# Placed in templates/ so the image runs envsubst on ${NGINX_LOCAL_RESOLVERS}
# at startup and writes the result to /etc/nginx/conf.d/default.conf.
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
