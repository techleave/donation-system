FROM node:24-alpine
WORKDIR /app
COPY . .
ENV NODE_ENV=production
ENV PORT=8080
EXPOSE 8080
CMD ["node","server.ts"]
