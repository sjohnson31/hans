# Development

## Requirements

- [git-lfs](https://git-lfs.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [portaudio](https://www.portaudio.com/)
- [clang](https://clang.llvm.org/)
- [mkcert](https://github.com/FiloSottile/mkcert)

## Setup

```bash
git clone --recurse-submodules -j8 git://github.com/sjohnson31/hans
# Set up certs
mkcert -install
mkcert -cert-file certs/hans.local.pem -key-file certs/hans.local-key.pem hans.local
# Add a hosts file entry for local hans server
echo "127.0.0.1 hans.local" | sudo tee -a /etc/hosts
```

## Run Hans

### Server

uv run --env-file .env --package server hans_server

### Client

uv run --env-file .env --package client hans_client

## Checkout submodules

Only necessary if --recurse-submodules not supplied on first checkout

```bash
git submodule update --init --recursive
```

## Get large files

Only necessary if git-lfs wasn't installed at first checkout

```bash
git lfs pull
```
