FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY packages/core/frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY packages/core/frontend/ .

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
