#!/bin/bash

# Blowhorn Network Designer - Deployment Script
# Comprehensive deployment options for any environment

set -e

echo "🚛 Blowhorn Network Designer - Deployment Options"
echo "================================================="

# Function to run dependency check
check_deps() {
    echo "🔍 Checking dependencies..."
    python3 check_dependencies.py
    return $?
}

# Function for local development setup
local_setup() {
    echo "🖥️  Setting up local development environment..."
    ./setup.sh
    
    if check_deps; then
        echo "✅ Local setup complete!"
        echo "🚀 Starting application..."
        ./run.sh
    else
        echo "❌ Setup failed. Please check error messages above."
        exit 1
    fi
}

# Function for Docker deployment
docker_setup() {
    echo "🐳 Setting up Docker deployment..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker first."
        exit 1
    fi
    
    echo "🔨 Building Docker image..."
    docker build -t blowhorn-network-designer .
    
    echo "🚀 Starting container..."
    docker run -p 8501:8501 blowhorn-network-designer
}

# Function for Docker Compose deployment
compose_setup() {
    echo "🐳 Setting up Docker Compose deployment..."
    
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose not found. Please install Docker Compose first."
        exit 1
    fi
    
    echo "🚀 Starting with Docker Compose..."
    docker-compose up --build
}

# Function for production deployment
production_setup() {
    echo "🏭 Setting up production environment..."
    
    # Create production virtual environment
    python3 -m venv prod_venv
    source prod_venv/bin/activate
    
    # Install production dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Run dependency check
    if check_deps; then
        echo "✅ Production setup complete!"
        echo "🚀 Starting production server..."
        streamlit run main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
    else
        echo "❌ Production setup failed."
        exit 1
    fi
}

# Main menu
echo ""
echo "Choose deployment option:"
echo "1) Local Development (recommended for testing)"
echo "2) Docker Container (isolated environment)"
echo "3) Docker Compose (with volume mounting)"
echo "4) Production Deployment (headless server)"
echo "5) Just check dependencies"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        local_setup
        ;;
    2)
        docker_setup
        ;;
    3)
        compose_setup
        ;;
    4)
        production_setup
        ;;
    5)
        check_deps
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac