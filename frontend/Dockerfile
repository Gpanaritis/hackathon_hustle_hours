FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3001

CMD ["npx", "next", "start", "--hostname", "0.0.0.0", "--port", "3001"]
