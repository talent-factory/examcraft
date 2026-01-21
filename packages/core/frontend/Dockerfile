FROM node:18-alpine

# Set working directory to workspace root
WORKDIR /workspace

# Copy root package.json and package-lock.json for workspace
COPY package*.json ./

# Copy all package.json files for workspace packages
COPY packages/core/frontend/package*.json ./packages/core/frontend/
COPY packages/premium/frontend/package*.json ./packages/premium/frontend/
COPY packages/enterprise/frontend/package*.json ./packages/enterprise/frontend/

# Install all workspace dependencies
RUN npm install

# Copy all source code
COPY packages/core/frontend/ ./packages/core/frontend/
COPY packages/premium/frontend/ ./packages/premium/frontend/
COPY packages/enterprise/frontend/ ./packages/enterprise/frontend/

# Set working directory to core frontend for running the app
WORKDIR /workspace/packages/core/frontend

# Copy entrypoint script
COPY packages/core/frontend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port
EXPOSE 3000

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start the application
CMD ["npm", "start"]
