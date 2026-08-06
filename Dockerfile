# Vanilla bootstrap image (circles): serves the hello page so the deploy pipeline is E2E-provable
# on day one. Replaced by the real product image via specs — never grow it in place.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY dist/ /usr/share/nginx/html/
