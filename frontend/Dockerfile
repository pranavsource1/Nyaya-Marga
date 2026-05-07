# Development Dockerfile for Next.js Frontend
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Ensure public directory exists
RUN mkdir -p ./public

EXPOSE 3000

# Dev mode with hot reload
CMD ["npm", "run", "dev"]
