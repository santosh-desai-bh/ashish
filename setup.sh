#!/bin/bash

# Blowhorn Network Designer - Foolproof Setup Script
# This script sets up the complete environment for the logistics network designer

set -e  # Exit on any error

echo "🚛 Blowhorn Network Designer - Environment Setup"
echo "================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Verify critical imports
echo "🧪 Verifying installations..."
python3 -c "
import streamlit
import pandas
import folium
import streamlit_folium
import sklearn
import shapely
import numpy
print('✅ All core dependencies verified')
"

# Check for GeoJSON file
if [ ! -f "bengaluru.geojson" ]; then
    echo "⚠️  WARNING: bengaluru.geojson not found"
    echo "   Pincode boundaries will not be available"
    echo "   You can download it from: https://github.com/datameet/Bangalore/tree/master/data"
else
    echo "✅ Bangalore GeoJSON boundaries found"
fi

# Create run script
cat > run.sh << 'EOF'
#!/bin/bash
echo "🚛 Starting Blowhorn Network Designer..."
source venv/bin/activate
streamlit run main.py --server.port 8501 --server.address 0.0.0.0
EOF

chmod +x run.sh

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "To start the application:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  streamlit run main.py"
echo ""
echo "The app will be available at: http://localhost:8501"
echo ""