# Crommix AI demo site: ai.crommixmali.com
# Stage 1 compiles the JS runtimes of the models; stage 2 serves everything with nginx.
FROM node:22-alpine AS js
WORKDIR /build/js
COPY js/package.json js/package-lock.json* js/tsconfig.json ./
COPY js/src ./src
RUN npm ci --ignore-scripts || npm install --ignore-scripts
RUN npx tsc -p tsconfig.json

FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/
# Each model ships as /vendor/<module>/{dist,model}. Add future models the same way.
COPY --from=js /build/js/dist /usr/share/nginx/html/vendor/cmx-lid/dist
COPY js/model /usr/share/nginx/html/vendor/cmx-lid/model
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/healthz || exit 1
