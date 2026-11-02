FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY infrastructure/azure/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
