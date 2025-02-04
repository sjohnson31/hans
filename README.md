# Development

## Requirements

- [git-lfs](https://git-lfs.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [portaudio](https://www.portaudio.com/)
- [clang](https://clang.llvm.org/)

## Clone

```bash
git clone --recurse-submodules -j8 git://github.com/sjohnson31/hans
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

Only necessary if git-lfs wasn't installed at first checkout and you want to run transcribe tests

```bash
git lfs pull
```
