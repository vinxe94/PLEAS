"""Runtime efficiency analyzer module."""
import time
import timeit
import sys
import os


def analyze_runtime(source_code):
    """Measure execution time, CPU usage, startup time, throughput."""
    result = {
        'success': False,
        'execution_time': {},
        'startup_time': 0,
        'throughput': {},
        'benchmark_results': [],
        'statistics': {},
        'rankings': {},
        'error': None,
    }

    try:
        code_obj = compile(source_code, '<user_input>', 'exec')
        safe_globals = {'__builtins__': __builtins__}

        # Measure startup/compilation time
        start = time.perf_counter()
        compile(source_code, '<user_input>', 'exec')
        startup_time = (time.perf_counter() - start) * 1000
        result['startup_time'] = round(startup_time, 4)

        # Single execution time
        start = time.perf_counter()
        try:
            exec(code_obj, safe_globals.copy(), {})
        except Exception:
            pass
        single_exec = (time.perf_counter() - start) * 1000

        # Multiple executions for statistics
        times = []
        iterations = 50
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                exec(code_obj, safe_globals.copy(), {})
            except Exception:
                pass
            times.append((time.perf_counter() - start) * 1000)

        result['execution_time'] = {
            'single_ms': round(single_exec, 4),
            'avg_ms': round(sum(times) / len(times), 4),
            'min_ms': round(min(times), 4),
            'max_ms': round(max(times), 4),
            'median_ms': round(sorted(times)[len(times) // 2], 4),
            'iterations': iterations,
        }

        # Throughput (executions per second)
        total_time_s = sum(times) / 1000
        throughput = iterations / max(total_time_s, 0.00001)
        result['throughput'] = {
            'executions_per_second': round(throughput, 2),
            'avg_response_time_ms': round(sum(times) / len(times), 4),
        }

        # Statistics
        import statistics
        result['statistics'] = {
            'mean': round(statistics.mean(times), 4),
            'stdev': round(statistics.stdev(times), 4) if len(times) > 1 else 0,
            'variance': round(statistics.variance(times), 6) if len(times) > 1 else 0,
            'p95': round(sorted(times)[int(0.95 * len(times))], 4),
            'p99': round(sorted(times)[int(0.99 * len(times))], 4),
        }

        # Benchmark comparison categories
        result['benchmark_results'] = [
            {'metric': 'Compilation Time', 'value': result['startup_time'], 'unit': 'ms', 'rating': rate_metric(result['startup_time'], 1, 5, 20)},
            {'metric': 'Average Execution', 'value': result['execution_time']['avg_ms'], 'unit': 'ms', 'rating': rate_metric(result['execution_time']['avg_ms'], 1, 10, 50)},
            {'metric': 'Throughput', 'value': result['throughput']['executions_per_second'], 'unit': 'ops/s', 'rating': rate_throughput(throughput)},
            {'metric': 'Consistency (StdDev)', 'value': result['statistics']['stdev'], 'unit': 'ms', 'rating': rate_metric(result['statistics']['stdev'], 0.1, 1, 5)},
            {'metric': 'Response Time (p95)', 'value': result['statistics']['p95'], 'unit': 'ms', 'rating': rate_metric(result['statistics']['p95'], 2, 15, 60)},
        ]

        # Rankings
        result['rankings'] = compute_rankings(result)
        result['success'] = True

    except SyntaxError as e:
        result['error'] = f"Syntax Error: {str(e)}"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result


def rate_metric(value, good, medium, poor):
    """Rate a metric as excellent/good/average/poor."""
    if value <= good:
        return {'label': 'Excellent', 'color': 'success', 'score': 95}
    elif value <= medium:
        return {'label': 'Good', 'color': 'info', 'score': 75}
    elif value <= poor:
        return {'label': 'Average', 'color': 'warning', 'score': 50}
    else:
        return {'label': 'Poor', 'color': 'danger', 'score': 25}


def rate_throughput(value):
    if value >= 10000:
        return {'label': 'Excellent', 'color': 'success', 'score': 95}
    elif value >= 1000:
        return {'label': 'Good', 'color': 'info', 'score': 75}
    elif value >= 100:
        return {'label': 'Average', 'color': 'warning', 'score': 50}
    else:
        return {'label': 'Poor', 'color': 'danger', 'score': 25}


def compute_rankings(result):
    """Compute overall performance rankings."""
    scores = [b['rating']['score'] for b in result['benchmark_results']]
    avg_score = sum(scores) / len(scores) if scores else 0
    if avg_score >= 85:
        tier = 'S'
    elif avg_score >= 70:
        tier = 'A'
    elif avg_score >= 55:
        tier = 'B'
    elif avg_score >= 40:
        tier = 'C'
    else:
        tier = 'D'

    return {
        'overall_score': round(avg_score, 1),
        'tier': tier,
        'category_scores': {b['metric']: b['rating']['score'] for b in result['benchmark_results']},
    }
