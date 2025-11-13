#!/bin/bash
# Quick Start Script für DTW Baseline Analyse
# ==========================================
#
# Usage: ./run_baseline.sh [limit]
#   limit: Anzahl Trajektorien (default: 100)
#
# Beispiel:
#   ./run_baseline.sh 50      # Nur 50 Trajektorien (schneller Test)
#   ./run_baseline.sh 500     # 500 Trajektorien (vollständige Analyse)

set -e  # Exit on error

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

LIMIT=${1:-100}

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}DTW Baseline Analysis - Quick Start${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Schritt 1: Python Dependencies
echo -e "${GREEN}[1/3] Checking Python dependencies...${NC}"
if ! python3 -c "import asyncpg, scipy" 2>/dev/null; then
    echo "  Installing Python dependencies..."
    pip install -q -r requirements.txt
    echo "  ✓ Dependencies installed"
else
    echo "  ✓ Dependencies OK"
fi
echo ""

# Schritt 2: Daten exportieren
echo -e "${GREEN}[2/3] Exporting trajectories from database...${NC}"
echo "  Limit: ${LIMIT} trajectories"

cd ../backend/scripts
python3 export_trajectories_for_matlab.py \
    --output ./matlab_data \
    --limit ${LIMIT}

if [ $? -eq 0 ]; then
    echo ""
    echo -e "  ${GREEN}✓ Export successful${NC}"
else
    echo -e "  ${RED}✗ Export failed${NC}"
    exit 1
fi
echo ""

# Schritt 3: MATLAB Analyse
echo -e "${GREEN}[3/3] Running MATLAB analysis...${NC}"
echo "  (This may take several minutes)"
echo ""

cd ../../matlab_analysis

# Check if MATLAB is available
if command -v matlab &> /dev/null; then
    matlab -nodisplay -nosplash -r "try; dtw_baseline_analysis; catch e; disp(e.message); exit(1); end; exit(0);"

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ MATLAB analysis completed${NC}"
    else
        echo -e "${RED}✗ MATLAB analysis failed${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ MATLAB not found in PATH${NC}"
    echo ""
    echo "Please run the analysis manually in MATLAB:"
    echo "  >> cd $(pwd)"
    echo "  >> dtw_baseline_analysis"
    exit 1
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Analysis Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Results saved in:"
echo "  - dtw_baseline_results.mat"
echo "  - dtw_vs_embedding_scatter.png"
echo "  - distance_distributions.png"
echo "  - precision_at_k_distribution.png"
echo ""
echo "To analyze specific queries:"
echo "  >> analyze_specific_query(5, '../backend/scripts/matlab_data/trajectories.mat', 'dtw_baseline_results.mat')"
echo ""
