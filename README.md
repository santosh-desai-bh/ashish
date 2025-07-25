# 🚛 Blowhorn Network Designer

**AI-powered logistics network optimization tool for warehouse placement and capacity planning**

## 🎯 Features

- **Smart Warehouse Placement**: DBSCAN clustering for optimal auxiliary warehouse locations
- **Coverage-First Design**: Every order cluster gets coverage regardless of distance to main warehouses
- **Pincode-Based Boundaries**: No overlapping coverage areas - clear driver territories
- **Real-time Cost Analysis**: Warehouse rent, people costs, and transportation breakdowns
- **Fleet Requirements**: First mile, middle mile, and last mile vehicle calculations
- **Interactive Map**: Toggle coverage areas, warehouse details, and order density visualization

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
./setup.sh
./run.sh
```

### Option 2: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start application
streamlit run main.py
```

## 📋 Requirements

- **Python**: 3.8+
- **Dependencies**: Listed in `requirements.txt`
- **Optional**: `bengaluru.geojson` for pincode boundaries

## 📁 Project Structure

```
├── main.py                     # Main Streamlit application
├── warehouse_logic.py          # Core warehouse placement algorithms
├── dbscan_warehouse_logic.py   # DBSCAN clustering for auxiliaries
├── visualization.py            # Map rendering and layers
├── simple_analytics.py         # Cost calculations and fleet requirements
├── data_processing.py          # Order data processing utilities
├── requirements.txt            # Python dependencies
├── setup.sh                   # Automated environment setup
└── README.md                  # This file
```

## 🗺️ Data Format

Upload a CSV file with these required columns:
- `created_date`: Order date
- `pickup_long`, `pickup_lat`: Customer pickup coordinates
- `order_long`, `order_lat`: Delivery location coordinates
- `customer`: Customer name (optional)

## 🔧 Key Algorithms

### DBSCAN Clustering
- **Purpose**: Find natural order density clusters for auxiliary placement
- **Coverage-First**: Places auxiliaries wherever orders cluster, regardless of main warehouse distance
- **Thresholds**: 70+ orders for 3km radius, scales with delivery distance

### Pincode Boundaries
- **No Overlaps**: Uses real administrative boundaries instead of circular coverage
- **Driver Clarity**: Clear territorial assignments for order allocation
- **Fallback**: Circle coverage if pincode data unavailable

### Cost Optimization
- **Fixed Main Warehouses**: 5 strategically placed for Bangalore geography
- **Dynamic Auxiliaries**: DBSCAN places auxiliaries where orders naturally cluster
- **Realistic Fleet**: Vehicle selection based on capacity and delivery radius

## 🎛️ Configuration

### Network Settings
- **Delivery Radius**: 2km/3km/5km last mile delivery distance
- **Capacity Planning**: Design for peak demand or typical demand
- **Target Daily Orders**: Slider to plan network capacity

### Map Layers (Toggle)
- **Order Locations**: Clustered order markers
- **Customer Pickup Locations**: Blue bubble sizes by volume
- **Main Warehouses**: Red squares with capacity indicators
- **Auxiliary Warehouses**: Green squares with coverage areas
- **Warehouse Coverage Areas**: Pincode boundaries or circles
- **Pincode Coverage Areas**: Exact administrative boundaries

## 📊 Analytics Dashboard

### Network Overview
- Main hubs, auxiliaries, coverage %, monthly volume

### Fleet Requirements
- **First Mile**: Customer pickups to main warehouses
- **Middle Mile**: Main warehouses to auxiliary restocking
- **Last Mile**: Auxiliary to customer delivery

### Cost Analysis
- Warehouse rent, people costs, transportation breakdown
- Cost per order and monthly totals
- Efficiency insights and recommendations

## 🐛 Troubleshooting

### Common Issues

**No auxiliary warehouses created:**
```bash
# Check debug output in terminal
# Look for DBSCAN clustering messages
# Verify order density meets thresholds
```

**Module not found errors:**
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
```

**GeoJSON boundaries not working:**
```bash
# Download bengaluru.geojson
# Place in project root directory  
# Restart application
```

### Debug Mode
The application includes comprehensive debug logging. Check terminal output for:
- DBSCAN clustering details
- Order density analysis
- Auxiliary placement decisions
- Coverage calculations

## 🎯 Coverage Philosophy

**Every order should be covered by either a main warehouse or auxiliary warehouse.**

The system prioritizes coverage over distance efficiency:
1. **Find Order Clusters**: DBSCAN identifies natural density areas
2. **Coverage Check**: Are orders efficiently served by existing warehouses?
3. **Create Auxiliary**: If no, place auxiliary regardless of distance to main warehouses
4. **Pincode Assignment**: Assign exact administrative boundaries for clear territories

## 🚀 Performance Tips

- Use **Representative Daily Sample** for consistent results
- Enable **Warehouse Coverage Areas** for debugging placement
- Check **Pincode Coverage Areas** for driver territory clarity
- Monitor debug output for clustering insights

## 📈 Scaling

The system is designed to handle:
- **Orders**: 500-5000 daily orders
- **Geography**: Bangalore metropolitan area
- **Warehouses**: 5 fixed main + dynamic auxiliaries
- **Coverage**: 95%+ order coverage target

---

**Built for Blowhorn Logistics** | **Powered by DBSCAN & Streamlit**