# Multi-stage build for apc-cluster-daemon (testbed/clustering-go).
FROM golang:1.22-bookworm AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /apc-cluster-daemon .

FROM gcr.io/distroless/static-debian12
COPY --from=build /apc-cluster-daemon /apc-cluster-daemon
ENTRYPOINT ["/apc-cluster-daemon"]
