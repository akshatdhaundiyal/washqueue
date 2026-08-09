# Use Node 20 slim image for development build
FROM node:20-slim

WORKDIR /app

# Copy package configurations
COPY package*.json ./

# Install npm dependencies
RUN npm install

# Copy frontend source code
COPY . .

# Set default host and port configurations for dev server in Docker
ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000

# Execute Nuxt dev server exposed to host network
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
