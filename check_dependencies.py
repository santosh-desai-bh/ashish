#!/usr/bin/env python3
"""
Dependency Check Script for Blowhorn Network Designer
Verifies all required packages are installed and working
"""

import sys
import importlib
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. Found: {version.major}.{version.minor}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_package(package_name, import_name=None, min_version=None):
    """Check if a package is installed and importable"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        
        # Check version if specified
        if min_version and hasattr(module, '__version__'):
            installed_version = module.__version__
            print(f"✅ {package_name}: {installed_version}")
        else:
            print(f"✅ {package_name}: installed")
        return True
        
    except ImportError as e:
        print(f"❌ {package_name}: not installed ({e})")
        return False

def check_file_exists(filepath, description):
    """Check if required files exist"""
    path = Path(filepath)
    if path.exists():
        print(f"✅ {description}: found")
        return True
    else:
        print(f"⚠️  {description}: not found (optional)")
        return False

def main():
    """Run all dependency checks"""
    print("🔍 Blowhorn Network Designer - Dependency Check")
    print("=" * 50)
    
    all_good = True
    
    # Check Python version
    if not check_python_version():
        all_good = False
    
    print("\n📦 Core Dependencies:")
    # Core packages
    required_packages = [
        ("streamlit", "streamlit"),
        ("pandas", "pandas"), 
        ("numpy", "numpy"),
        ("folium", "folium"),
        ("streamlit-folium", "streamlit_folium"),
        ("scikit-learn", "sklearn"),
        ("shapely", "shapely"),
    ]
    
    for package_name, import_name in required_packages:
        if not check_package(package_name, import_name):
            all_good = False
    
    print("\n📁 Optional Files:")
    # Optional files
    check_file_exists("bengaluru.geojson", "Bangalore GeoJSON boundaries")
    
    print("\n🧪 Functional Tests:")
    # Test critical functionality
    try:
        from sklearn.cluster import DBSCAN
        print("✅ DBSCAN clustering: available")
    except ImportError:
        print("❌ DBSCAN clustering: failed")
        all_good = False
    
    try:
        from shapely.geometry import Point, Polygon
        print("✅ Shapely geometry: available")
    except ImportError:
        print("❌ Shapely geometry: failed")
        all_good = False
    
    try:
        import folium
        test_map = folium.Map()
        print("✅ Folium mapping: available")
    except Exception:
        print("❌ Folium mapping: failed")
        all_good = False
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("🎉 All dependencies satisfied!")
        print("✅ Ready to run: streamlit run main.py")
        return 0
    else:
        print("❌ Some dependencies missing.")
        print("💡 Run: ./setup.sh to install missing packages")
        return 1

if __name__ == "__main__":
    exit(main())