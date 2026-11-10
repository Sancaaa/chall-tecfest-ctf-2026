# warmup_web_diluc - Web Exploitation Warm-up (flag tersebar di client-side source)
# TODO sebelum deploy: ganti tag ke digest spesifik (docker pull nginx:1.27-alpine
# lalu `docker inspect --format='{{index .RepoDigests 0}}'`), ikuti aturan pin-image
# di CHALLENGE_DAN_HOSTING.md. Belum di-pin di sini karena Docker Desktop tidak
# nyala saat dibuat.
FROM nginx:1.27-alpine

COPY site/ /usr/share/nginx/html/

RUN chmod -R a-w /usr/share/nginx/html

EXPOSE 80
