"""Hot path detection and runtime profiling module."""
import cProfile
import pstats
import io
import time
import ast
from collections import defaultdict


def analyze_hotpath(source_code):
    """Profile code and detect hot paths."""
    result = {
        'success': False,
        'profile_stats': [],
        'hot_functions': [],
        'execution_timeline': [],
        'bottlenecks': [],
        'call_frequency': {},
        'total_time': 0,
        'total_calls': 0,
        'line_frequency': {},
        'error': None,
    }

    try:
        # Profile with cProfile
        profiler = cProfile.Profile()
        safe_globals = {'__builtins__': __builtins__}
        code_obj = compile(source_code, '<user_input>', 'exec')

        profiler.enable()
        start = time.perf_counter()
        try:
            exec(code_obj, safe_globals, {})
        except Exception as e:
            pass
        elapsed = time.perf_counter() - start
        profiler.disable()

        result['total_time'] = round(elapsed * 1000, 4)

        # Parse stats
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(30)

        raw_stats = stream.getvalue()

        # Extract function stats
        for func_key, func_stat in profiler.stats.items():
            filename, line, name = func_key
            ncalls, totcalls, tottime, cumtime, callers = func_stat
            result['profile_stats'].append({
                'function': name,
                'file': filename,
                'line': line,
                'ncalls': ncalls,
                'tottime_ms': round(tottime * 1000, 4),
                'cumtime_ms': round(cumtime * 1000, 4),
                'percall_ms': round((tottime / max(ncalls, 1)) * 1000, 6),
            })
            result['total_calls'] += ncalls

        # Sort by cumulative time
        result['profile_stats'].sort(key=lambda x: x['cumtime_ms'], reverse=True)

        # Identify hot functions (top 20% by time)
        if result['profile_stats']:
            threshold = result['profile_stats'][0]['cumtime_ms'] * 0.2
            result['hot_functions'] = [
                s for s in result['profile_stats'] if s['cumtime_ms'] >= threshold
            ][:10]

        # Call frequency
        result['call_frequency'] = {
            s['function']: s['ncalls'] for s in result['profile_stats'][:15]
        }

        # Detect bottlenecks
        for stat in result['profile_stats'][:5]:
            if stat['tottime_ms'] > 0.1:
                result['bottlenecks'].append({
                    'function': stat['function'],
                    'time_ms': stat['tottime_ms'],
                    'calls': stat['ncalls'],
                    'severity': 'high' if stat['tottime_ms'] > 1 else 'medium',
                    'suggestion': f"Function '{stat['function']}' consumes significant time ({stat['tottime_ms']:.2f}ms). Consider optimizing.",
                })

        # Line-level analysis via AST
        tree = ast.parse(source_code)
        line_types = {}
        for node in ast.walk(tree):
            if hasattr(node, 'lineno'):
                node_type = type(node).__name__
                if node.lineno not in line_types:
                    line_types[node.lineno] = []
                line_types[node.lineno].append(node_type)

        # Detect loops as potential hot paths
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                result['line_frequency'][f"Line {node.lineno}"] = {
                    'type': 'loop',
                    'construct': type(node).__name__,
                    'is_hot': True,
                }

        # Build execution timeline
        timeline_entries = []
        for i, stat in enumerate(result['profile_stats'][:10]):
            timeline_entries.append({
                'order': i + 1,
                'function': stat['function'],
                'duration_ms': stat['cumtime_ms'],
                'calls': stat['ncalls'],
            })
        result['execution_timeline'] = timeline_entries

        result['success'] = True

    except SyntaxError as e:
        result['error'] = f"Syntax Error: {str(e)}"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result
