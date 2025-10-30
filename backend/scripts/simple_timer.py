# backend/scripts/benchmarks/simple_timer.py

import asyncio
import time
import json
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
import os

# ✅ FIX: Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# ✅ Now absolute imports work
from app.database import get_db_pool
from app.utils.multi_modal_searcher import MultiModalSearcher

# ✅ GLOBAL CONFIG
MODES = ['position', 'joint', 'orientation', 'velocity', 'acceleration']
WEIGHTS = {'position': 0.3, 'joint': 0.2, 'orientation': 1.0, 'velocity': 0.5, 'acceleration': 0.5}
N_QUERIES = 10
N_RUNS = 1


async def get_random_bahn_ids(pool, n=20):
    """Hole n zufällige Bahn-IDs"""
    async with pool.acquire() as conn:
        query = """
            SELECT bahn_id
            FROM bewegungsdaten.bahn_metadata
            WHERE segment_id = bahn_id
            ORDER BY RANDOM()
            LIMIT $1
        """
        rows = await conn.fetch(query, n)
        return [row['bahn_id'] for row in rows]


async def run_benchmark():
    """Führe Performance-Test durch"""
    
    print("\n" + "="*50)
    print("🚀 Query Performance Benchmark")
    print("="*50 + "\n")
    
    # Setup
    pool = await get_db_pool()
    
    # Test-IDs
    print("📋 Selecting test queries...")
    test_ids = await get_random_bahn_ids(pool, n=N_QUERIES)
    print(f"   Selected {len(test_ids)} bahnen\n")
    
    # Results
    results = {}
    
    print("⏱️  Running tests...\n")
    
    # Run tests
    for i, bahn_id in enumerate(test_ids, 1):
        print(f"   [{i}/{len(test_ids)}] Testing {bahn_id}...", end=" ")
        
        times = []
        
        async with pool.acquire() as conn:
            searcher = MultiModalSearcher(conn)
            
            for run in range(N_RUNS):
                start = time.time()
                
                # ✅ Uses global MODES and WEIGHTS
                await searcher.search_similar(
                    target_id=bahn_id,
                    limit=100,
                    modes=MODES,
                    weights=WEIGHTS
                )
                
                elapsed_ms = (time.time() - start) * 1000
                times.append(elapsed_ms)
        
        results[bahn_id] = times
        print(f"{np.mean(times):.1f} ms")
    
    await pool.close()
    
    # Calculate stats
    all_times = [t for times in results.values() for t in times]
    
    stats = {
        'mean': float(np.mean(all_times)),
        'median': float(np.median(all_times)),
        'min': float(np.min(all_times)),
        'max': float(np.max(all_times)),
        'std': float(np.std(all_times))
    }
    
    # Print results
    print("\n" + "="*50)
    print("📊 Results")
    print("="*50)
    print(f"Queries tested:  {len(test_ids)} bahnen × {N_RUNS} runs")
    print(f"\nMean:            {stats['mean']:.1f} ms")
    print(f"Median:          {stats['median']:.1f} ms")
    print(f"Min:             {stats['min']:.1f} ms")
    print(f"Max:             {stats['max']:.1f} ms")
    print(f"Std Dev:         {stats['std']:.1f} ms")
    print("="*50 + "\n")
    
    # Save to file
    output = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'n_queries': len(test_ids),
            'runs_per_query': N_RUNS,
            'modes': MODES,          # ✅ Uses global
            'weights': WEIGHTS        # ✅ Uses global
        },
        'results': results,
        'stats': stats
    }
    
    # ✅ Save in benchmarks folder
    output_dir = Path(__file__).parent
    output_file = output_dir / 'benchmark_results.json'
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())