FROM php:8.4-cli

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

# Initialize environment
RUN cp .env.example .env

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader

# Generate application key
RUN php artisan key:generate

# Create the SQLite database file and run migrations/seeders
RUN touch database/database.sqlite && \
    php artisan migrate --force && \
    php artisan db:seed --force

# Ensure directories are writable
RUN chmod -R 777 storage bootstrap/cache database

# Expose the port (Render provides $PORT, defaults to 10000)
EXPOSE 10000

# Start the PHP server
CMD php artisan serve --host=0.0.0.0 --port=${PORT:-10000}
