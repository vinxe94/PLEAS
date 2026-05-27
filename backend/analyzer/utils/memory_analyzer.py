"""Memory overhead analyzer module."""
import tracemalloc
import gc
import sys
import time
import ast


def analyze_memory(source_code):
    """Analyze memory usage of provided code."""
    result = {
        'success': False,
        'heap_usage': {},
        'object_allocation': {},
        'gc_stats': {},
        'memory_timeline': [],
        'top_allocations': [],
        'stack_estimation': {},
        'summary': {},
        'error': None,
    }

    try:
        code_obj = compile(source_code, '<user_input>', 'exec')
        safe_globals = {'__builtins__': __builtins__}

        # Force garbage collection before measurement
        gc.collect()
        gc_stats_before = gc.get_stats()

        # Start tracemalloc
        tracemalloc.start(10)
        snapshot_before = tracemalloc.take_snapshot()

        # Memory timeline
        timeline = []
        exec_ns = {}

        # Execute in stages if possible
        lines = source_code.strip().split('\n')
        chunk_size = max(1, len(lines) // 10)

        start_time = time.perf_counter()
        try:
            exec(code_obj, safe_globals.copy(), exec_ns)
        except Exception:
            pass
        exec_time = time.perf_counter() - start_time

        snapshot_after = tracemalloc.take_snapshot()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Heap usage
        result['heap_usage'] = {
            'current_bytes': current,
            'current_kb': round(current / 1024, 2),
            'current_mb': round(current / (1024 * 1024), 4),
            'peak_bytes': peak,
            'peak_kb': round(peak / 1024, 2),
            'peak_mb': round(peak / (1024 * 1024), 4),
        }

        # Top allocations by file
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
        for stat in top_stats[:15]:
            result['top_allocations'].append({
                'file': str(stat.traceback),
                'size_bytes': stat.size,
                'size_kb': round(stat.size / 1024, 2),
                'count': stat.count,
                'size_diff': stat.size_diff,
            })

        # Object allocation analysis
        gc.collect()
        gc_stats_after = gc.get_stats()

        # Count objects by type
        object_counts = {}
        for obj in gc.get_objects():
            type_name = type(obj).__name__
            if type_name not in object_counts:
                object_counts[type_name] = {'count': 0, 'total_size': 0}
            object_counts[type_name]['count'] += 1
            try:
                object_counts[type_name]['total_size'] += sys.getsizeof(obj)
            except (TypeError, RecursionError):
                pass

        # Top objects by count
        sorted_objects = sorted(object_counts.items(), key=lambda x: x[1]['count'], reverse=True)[:15]
        result['object_allocation'] = {
            name: {
                'count': info['count'],
                'total_size_kb': round(info['total_size'] / 1024, 2),
            } for name, info in sorted_objects
        }

        # GC stats
        result['gc_stats'] = {
            'generations': [],
            'garbage_objects': len(gc.garbage),
            'gc_enabled': gc.isenabled(),
            'thresholds': gc.get_threshold(),
        }
        for i, (before, after) in enumerate(zip(gc_stats_before, gc_stats_after)):
            result['gc_stats']['generations'].append({
                'generation': i,
                'collections': after.get('collections', 0),
                'collected': after.get('collected', 0),
                'uncollectable': after.get('uncollectable', 0),
            })

        # Stack estimation via AST analysis
        tree = ast.parse(source_code)
        max_depth = 0
        func_count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_count += 1
            if isinstance(node, ast.Call):
                max_depth += 1

        result['stack_estimation'] = {
            'function_count': func_count,
            'call_sites': max_depth,
            'estimated_stack_frames': func_count + 1,
            'estimated_stack_kb': round((func_count + 1) * 8.0, 2),
            'recursion_limit': sys.getrecursionlimit(),
        }

        # Memory timeline simulation
        tracemalloc.start()
        for i in range(10):
            partial_lines = lines[:max(1, (i + 1) * chunk_size)]
            partial_code = '\n'.join(partial_lines)
            try:
                exec(compile(partial_code, '<partial>', 'exec'), safe_globals.copy(), {})
            except Exception:
                pass
            curr, _ = tracemalloc.get_traced_memory()
            timeline.append({
                'step': i + 1,
                'lines_executed': len(partial_lines),
                'memory_kb': round(curr / 1024, 2),
            })
        tracemalloc.stop()
        result['memory_timeline'] = timeline

        # Summary
        result['summary'] = {
            'total_memory_kb': result['heap_usage']['peak_kb'],
            'execution_time_ms': round(exec_time * 1000, 4),
            'objects_tracked': sum(info['count'] for _, info in sorted_objects),
            'gc_collections': sum(g.get('collections', 0) for g in gc_stats_after),
            'memory_efficiency': rate_memory(peak),
        }

        result['success'] = True

    except SyntaxError as e:
        result['error'] = f"Syntax Error: {str(e)}"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result


def rate_memory(peak_bytes):
    """Rate memory usage."""
    kb = peak_bytes / 1024
    if kb < 100:
        return {'label': 'Excellent', 'color': 'success', 'score': 95}
    elif kb < 500:
        return {'label': 'Good', 'color': 'info', 'score': 75}
    elif kb < 2000:
        return {'label': 'Average', 'color': 'warning', 'score': 50}
    else:
        return {'label': 'Heavy', 'color': 'danger', 'score': 25}
