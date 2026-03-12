FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY packages/core/frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY packages/core/frontend/ ./

# Set working directory for running the app
WORKDIR /app

# Copy entrypoint script (from build context root)
COPY packages/core/frontend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port
EXPOSE 3000

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start the application
CMD ["npm", "start"]
