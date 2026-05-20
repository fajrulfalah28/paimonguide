FROM php:8.2-cli

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libzip-dev \
    unzip \
    sqlite3 \
    libsqlite3-dev

# Install PHP extensions
RUN docker-php-ext-install zip pdo pdo_sqlite

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Set working directory
WORKDIR /app

# Copy the project files
COPY . .

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader

# Create the SQLite database file if it doesn't exist
RUN touch database/database.sqlite

# Expose the port (Render provides $PORT, defaults to 10000)
EXPOSE 10000

# Start the PHP server
CMD php -S 0.0.0.0:${PORT:-10000} -t public
