# Build the RLNC demo/service binary (testbed/rlnc-cpp).
FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN mkdir build && cd build && cmake .. && make -j"$(nproc)"

FROM debian:bookworm-slim
COPY --from=build /src/build/rlnc_demo /usr/local/bin/rlnc_demo
ENTRYPOINT ["/usr/local/bin/rlnc_demo"]
