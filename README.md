# Paimon Guide

The best travel companion ever! An unofficial Genshin Impact quest prerequisite chatbot that uses Named Entity Recognition (NER) to map out location and quest requirements. Tell Paimon where you want to go, and she will find the way!

## Features
- **Core Chatbot Logic:** Manages conversation flow, prerequisite handling, and API endpoints.
- **Named Entity Recognition (NER):** Extracts Genshin Impact locations from user text using a specialized NLP model.
- **Containerized Environment:** Easy local setup and deployment using Docker.

## Tech Stack
- **Backend API:** Laravel (PHP)
- **NER Service:** Flask (Python)
- **Database:** SQLite
- **Containerization:** Docker & Docker Compose

## Getting Started

### Requirements
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (for Docker installation)
- PHP & Composer (for manual local installation)
- Node.js & npm (for manual local installation)
- Python 3.8+ (for manual local installation)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

#### Method 1: Using Docker (Recommended)

Start the services using Docker Compose:
```bash
docker-compose up -d --build
```

The services will be available at:
- **Paimon Guide (Laravel API):** `http://localhost:10000`
- **NER Service (Python API):** `http://localhost:5000`

#### Method 2: Manual Local Installation

**1. Setup NER Service (Python API)**
```bash
cd ner-service
python -m venv venv
# On Windows use: venv\Scripts\activate
# On Linux/Mac use: source venv/bin/activate
pip install -r requirements.txt
python app.py
```
*The NER service will run on `http://localhost:5000`*

**2. Setup Paimon Guide (Laravel API)**
Open a new terminal and run:
```bash
cd paimon-guide
composer install
npm install
npm run build
cp .env.example .env
php artisan key:generate
php artisan migrate --seed
php artisan serve
```
*The Laravel API will run on `http://localhost:8000` by default.*

## Architecture

The system consists of two main components orchestrated by Docker Compose:

1. **paimon-guide (Laravel API):**
   - Serves as the main entry point for the chatbot.
   - Handles the core logic, SQLite database migrations/seeders, and manages prerequisites.
   - Communicates with the NER service to process natural language input.

2. **ner-service (Python Flask API):**
   - A dedicated microservice for Named Entity Recognition.
   - Runs the required NLP models to identify Genshin Impact locations from text.


