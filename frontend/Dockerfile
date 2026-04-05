FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy application files
COPY . .

# Expose port
EXPOSE 3000

# Command is overridden in docker-compose.yml
CMD ["npm", "run", "dev"]
