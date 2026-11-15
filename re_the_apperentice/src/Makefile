.PHONY: build test clean

build:
	GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -o ../dist/grimoire .

test:
	go test -v ./...

clean:
	rm -f ../dist/grimoire
