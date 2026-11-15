# Build binary attachment Naberius. Jalankan dari folder ini:
#   docker build --target out --output type=local,dest=dist .
# Hasil: dist/naberius (ELF x86-64, static, stripped).
# TODO sebelum lomba: pin base image lewat digest (golang:1.23-bookworm@sha256:...)
# supaya rebuild tidak diam-diam mengubah layout binary.
FROM golang:1.23-bookworm AS build
WORKDIR /src
COPY src/ .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -buildvcs=false -ldflags="-s -w -buildid=" -o /out/naberius .

FROM scratch AS out
COPY --from=build /out/naberius /naberius
