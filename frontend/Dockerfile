FROM oven/bun:1-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/bun.lock ./

# Install dependencies
RUN bun install

# Copy source code
COPY frontend/ ./

# Set working directory for running the app
WORKDIR /app

# Copy entrypoint script (from build context root)
COPY frontend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port
EXPOSE 3000

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start the application
CMD ["bun", "start"]
