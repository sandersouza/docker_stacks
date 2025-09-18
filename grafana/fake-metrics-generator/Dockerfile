FROM node:20-alpine AS build

RUN apk add --no-cache git

WORKDIR /src
RUN git clone --depth 1 https://github.com/grafana/fake-metrics-generator.git .

RUN corepack enable \
    && yarn install --frozen-lockfile \
    && yarn build

FROM node:20-alpine

WORKDIR /app
COPY --from=build /src/dist .

EXPOSE 5001

CMD ["node", "main.node.js"]
