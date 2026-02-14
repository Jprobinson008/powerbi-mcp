"""
Performance Benchmarking Tool for Power BI PBIP Connector

Helps identify bottlenecks and measure optimization impact.
Tests various scenarios with different project sizes and complexity.
"""
import os
import sys
import tempfile
import shutil
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from powerbi_pbip_connector import PowerBIPBIPConnector


def create_performance_test_project(
    temp_dir: str,
    num_tables: int = 10,
    num_visuals: int = 20,
    avg_table_size_kb: int = 10,
    use_pbir_enhanced: bool = True
) -> str:
    """
    Create a test PBIP project with configurable size and complexity.
    
    Args:
        temp_dir: Base temporary directory
        num_tables: Number of tables to create
        num_visuals: Number of visual.json files (PBIR Enhanced only)
        avg_table_size_kb: Average size per table in KB
        use_pbir_enhanced: Use PBIR Enhanced format (True) or PBIR Legacy (False)
    
    Returns:
        Path to created project
    """
    project_name = "PerfTest"
    project_dir = Path(temp_dir) / project_name
    pbip_file = project_dir / f"{project_name}.pbip"
    
    # Create directory structure
    semantic_dir = project_dir / f"{project_name}.SemanticModel"
    tables_dir = semantic_dir / "definition" / "tables"
    relationships_dir = semantic_dir / "definition" / "relationships"
    report_dir = project_dir / f"{project_name}.Report"
    
    os.makedirs(tables_dir, exist_ok=True)
    os.makedirs(relationships_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    
    # Create .pbip file
    with open(pbip_file, 'w') as f:
        f.write('{"version": "1.0"}')
    
    # Create tables with padding to reach desired size
    padding_per_table = "    " + "   " * (avg_table_size_kb * 100)  # Rough estimation
    
    for i in range(num_tables):
        table_name = f"Table_{i+1:03d}"
        safe_name = table_name if i % 3 != 0 else f"Table With Spaces_{i+1:03d}"
        
        columns = "\n".join([
            f"    column Column_{j+1:02d}\n        dataType: string"
            for j in range(5)
        ])
        
        measure = ""
        if i % 2 == 0:
            measure = f"""
    measure MeasureCount = COUNTROWS({table_name})
    measure MeasureSum = SUM({table_name}[Column_01])"""
        
        table_content = f"""table {safe_name}
{columns}
{measure}
{padding_per_table}
"""
        with open(tables_dir / f"{table_name}.tmdl", 'w') as f:
            f.write(table_content)
    
    # Create relationships
    for i in range(num_tables - 1):
        rel_content = f"""relationship rel_{i+1}
  cardinality: manyToOne
  fromTable: Table_{i+1:03d}
  fromColumn: Column_01
  toTable: Table_{i+2:03d}
  toColumn: Column_01
"""
        with open(relationships_dir / f"rel_{i+1}.tmdl", 'w') as f:
            f.write(rel_content)
    
    # Create PBIR format
    if use_pbir_enhanced:
        definition_dir = report_dir / "definition"
        pages_dir = definition_dir / "pages"
        os.makedirs(pages_dir, exist_ok=True)
        
        # Create report.json
        with open(definition_dir / "report.json", 'w') as f:
            f.write('{"version": "2.0"}')
        
        # Create pages structure with visuals
        pages_json = {"pages": [{"name": "Page1", "displayName": "Page 1"}]}
        with open(pages_dir / "pages.json", 'w') as f:
            json.dump(pages_json, f)
        
        # Create visual.json files
        for v in range(num_visuals):
            page_id = f"page_{(v // 5) + 1:02d}"
            visual_id = f"visual_{v+1:03d}"
            visual_dir = pages_dir / page_id / "visuals" / visual_id
            os.makedirs(visual_dir, exist_ok=True)
            
            visual_content = {
                "version": "1.0",
                "config": {
                    "type": "card",
                    "projections": {
                        "Values": [
                            {
                                "SourceRef": {
                                    "Entity": f"Table_{(v % num_tables) + 1:03d}",
                                    "Property": "Column_01"
                                }
                            }
                        ]
                    }
                }
            }
            
            with open(visual_dir / "visual.json", 'w') as f:
                json.dump(visual_content, f, indent=2)
    else:
        # Create PBIR Legacy: single report.json
        report_json = {
            "version": "1.0",
            "sections": []
        }
        with open(report_dir / "report.json", 'w') as f:
            json.dump(report_json, f)
    
    return str(project_dir)


def benchmark_operation(name: str, operation, *args, **kwargs) -> Tuple[float, any]:
    """
    Benchmark a single operation and return execution time and result.
    
    Args:
        name: Operation name for logging
        operation: Callable to benchmark
        *args: Arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation
    
    Returns:
        Tuple of (execution_time_ms, result)
    """
    start = time.perf_counter()
    result = operation(*args, **kwargs)
    end = time.perf_counter()
    
    elapsed_ms = (end - start) * 1000
    print(f"  {name}: {elapsed_ms:.2f}ms")
    
    return elapsed_ms, result


def run_benchmarks():
    """Run comprehensive performance benchmarks"""
    
    print("\n" + "=" * 70)
    print("POWER BI PBIP CONNECTOR - PERFORMANCE BENCHMARKS")
    print("=" * 70)
    
    results = {
        "benchmarks": [],
        "summary": {}
    }
    
    temp_dir = tempfile.mkdtemp(prefix="pbip_perf_test_")
    
    try:
        # Test 1: Small project
        print("\nBENCHMARK 1: Small Project (10 tables, 20 visuals)")
        print("-" * 70)
        
        project_path_small = create_performance_test_project(
            temp_dir, 
            num_tables=10, 
            num_visuals=20,
            avg_table_size_kb=5
        )
        
        connector = PowerBIPBIPConnector(auto_backup=False)
        
        # Load project
        elapsed, _ = benchmark_operation(
            "Load project",
            connector.load_project,
            project_path_small
        )
        results["benchmarks"].append({"operation": "load_small", "time_ms": elapsed})
        
        # Validate TMDL
        elapsed, _ = benchmark_operation(
            "Validate TMDL syntax",
            connector.validate_tmdl_syntax
        )
        results["benchmarks"].append({"operation": "validate_small", "time_ms": elapsed})
        
        # Fix DAX quoting
        elapsed, _ = benchmark_operation(
            "Fix DAX quoting",
            connector.fix_all_dax_quoting
        )
        results["benchmarks"].append({"operation": "fix_dax_small", "time_ms": elapsed})
        
        # Rename table
        elapsed, _ = benchmark_operation(
            "Rename table",
            connector.rename_table_in_files,
            "Table_001",
            "Renamed Table"
        )
        results["benchmarks"].append({"operation": "rename_table_small", "time_ms": elapsed})
        
        # Test 2: Medium project
        print("\nBENCHMARK 2: Medium Project (50 tables, 100 visuals)")
        print("-" * 70)
        
        project_path_medium = create_performance_test_project(
            temp_dir,
            num_tables=50,
            num_visuals=100,
            avg_table_size_kb=10
        )
        
        connector2 = PowerBIPBIPConnector(auto_backup=False)
        
        elapsed, _ = benchmark_operation(
            "Load project",
            connector2.load_project,
            project_path_medium
        )
        results["benchmarks"].append({"operation": "load_medium", "time_ms": elapsed})
        
        elapsed, _ = benchmark_operation(
            "Validate TMDL syntax",
            connector2.validate_tmdl_syntax
        )
        results["benchmarks"].append({"operation": "validate_medium", "time_ms": elapsed})
        
        elapsed, _ = benchmark_operation(
            "Fix DAX quoting",
            connector2.fix_all_dax_quoting
        )
        results["benchmarks"].append({"operation": "fix_dax_medium", "time_ms": elapsed})
        
        # Test 3: Large project
        print("\nBENCHMARK 3: Large Project (200 tables, 500 visuals)")
        print("-" * 70)
        
        project_path_large = create_performance_test_project(
            temp_dir,
            num_tables=200,
            num_visuals=500,
            avg_table_size_kb=15
        )
        
        connector3 = PowerBIPBIPConnector(auto_backup=False)
        
        elapsed, _ = benchmark_operation(
            "Load project",
            connector3.load_project,
            project_path_large
        )
        results["benchmarks"].append({"operation": "load_large", "time_ms": elapsed})
        
        elapsed, _ = benchmark_operation(
            "Validate TMDL syntax",
            connector3.validate_tmdl_syntax
        )
        results["benchmarks"].append({"operation": "validate_large", "time_ms": elapsed})
        
        elapsed, _ = benchmark_operation(
            "Fix DAX quoting",
            connector3.fix_all_dax_quoting
        )
        results["benchmarks"].append({"operation": "fix_dax_large", "time_ms": elapsed})
        
        # Summary analysis
        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")  
        print("=" * 70)
        
        small_ops = [b for b in results["benchmarks"] if "small" in b["operation"]]
        medium_ops = [b for b in results["benchmarks"] if "medium" in b["operation"]]
        large_ops = [b for b in results["benchmarks"] if "large" in b["operation"]]
        
        print(f"\nSmall Project Average: {sum(b['time_ms'] for b in small_ops) / len(small_ops):.2f}ms")
        print(f"Medium Project Average: {sum(b['time_ms'] for b in medium_ops) / len(medium_ops):.2f}ms")
        print(f"Large Project Average: {sum(b['time_ms'] for b in large_ops) / len(large_ops):.2f}ms")
        
        # Scaling analysis
        if small_ops and large_ops:
            small_avg = sum(b['time_ms'] for b in small_ops) / len(small_ops)
            large_avg = sum(b['time_ms'] for b in large_ops) / len(large_ops)
            scaling_factor = large_avg / small_avg if small_avg > 0 else 0
            print(f"\nScaling Factor (Large vs Small): {scaling_factor:.1f}x")
            print(f"Table growth: 10 -> 200 (20x)")
            print(f"Time growth: ~{scaling_factor:.1f}x")
            if scaling_factor < 30:
                print(f"✓ Sub-linear scaling! Performance is good.")
            elif scaling_factor < 100:
                print(f"⚠ Linear scaling. Consider parallelization for very large projects.")
            else:
                print(f"⚠ Super-linear scaling. Possible optimization needed.")
        
        results["summary"] = {
            "small_avg_ms": sum(b['time_ms'] for b in small_ops) / len(small_ops),
            "medium_avg_ms": sum(b['time_ms'] for b in medium_ops) / len(medium_ops),
            "large_avg_ms": sum(b['time_ms'] for b in large_ops) / len(large_ops),
        }
        
        # Save results
        with open('benchmark_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n✓ Results saved to benchmark_results.json")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    run_benchmarks()
