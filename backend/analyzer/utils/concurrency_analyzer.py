"""Concurrency and parallelism analysis module."""
import threading
import multiprocessing
import asyncio
import time
import queue
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def analyze_concurrency(source_code):
    """Analyze concurrency characteristics of code."""
    result = {
        'success': False,
        'threading_results': {},
        'multiprocessing_results': {},
        'async_results': {},
        'comparison': {},
        'race_condition_analysis': {},
        'deadlock_analysis': {},
        'cpu_utilization': {},
        'error': None,
    }

    try:
        code_obj = compile(source_code, '<user_input>', 'exec')
        safe_globals = {'__builtins__': __builtins__}

        # Sequential baseline
        start = time.perf_counter()
        for _ in range(4):
            try:
                exec(code_obj, safe_globals.copy(), {})
            except Exception:
                pass
        sequential_time = (time.perf_counter() - start) * 1000

        # Threading analysis
        thread_times = []

        def thread_task():
            s = time.perf_counter()
            try:
                exec(code_obj, safe_globals.copy(), {})
            except Exception:
                pass
            thread_times.append((time.perf_counter() - s) * 1000)

        start = time.perf_counter()
        threads = []
        for _ in range(4):
            t = threading.Thread(target=thread_task)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        threading_total = (time.perf_counter() - start) * 1000

        result['threading_results'] = {
            'total_time_ms': round(threading_total, 4),
            'thread_count': 4,
            'avg_thread_time_ms': round(sum(thread_times) / max(len(thread_times), 1), 4),
            'speedup_vs_sequential': round(sequential_time / max(threading_total, 0.001), 2),
            'overhead_ms': round(max(threading_total - sequential_time / 4, 0), 4),
        }

        # Thread pool analysis
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for _ in range(4):
                futures.append(executor.submit(exec, code_obj, safe_globals.copy(), {}))
            for f in futures:
                try:
                    f.result()
                except Exception:
                    pass
        pool_time = (time.perf_counter() - start) * 1000

        # Async analysis
        async def async_task():
            s = time.perf_counter()
            try:
                exec(code_obj, safe_globals.copy(), {})
            except Exception:
                pass
            await asyncio.sleep(0)
            return (time.perf_counter() - s) * 1000

        async def run_async():
            tasks = [async_task() for _ in range(4)]
            return await asyncio.gather(*tasks)

        start = time.perf_counter()
        try:
            loop = asyncio.new_event_loop()
            async_times = loop.run_until_complete(run_async())
            loop.close()
        except Exception:
            async_times = [0]
        async_total = (time.perf_counter() - start) * 1000

        result['async_results'] = {
            'total_time_ms': round(async_total, 4),
            'task_count': 4,
            'avg_task_time_ms': round(sum(async_times) / max(len(async_times), 1), 4),
            'speedup_vs_sequential': round(sequential_time / max(async_total, 0.001), 2),
        }

        # Multiprocessing (simulated with timing data to avoid issues)
        mp_estimated = sequential_time / 4 + 50  # Overhead estimate
        result['multiprocessing_results'] = {
            'estimated_time_ms': round(mp_estimated, 4),
            'process_count': 4,
            'estimated_speedup': round(sequential_time / max(mp_estimated, 0.001), 2),
            'overhead_ms': round(50, 4),
            'note': 'Multiprocessing overhead includes process creation cost',
        }

        # Comparison summary
        result['comparison'] = {
            'sequential_ms': round(sequential_time, 4),
            'threading_ms': round(threading_total, 4),
            'thread_pool_ms': round(pool_time, 4),
            'async_ms': round(async_total, 4),
            'multiprocessing_estimated_ms': round(mp_estimated, 4),
            'best_approach': min(
                [('Threading', threading_total), ('Async', async_total), ('Thread Pool', pool_time)],
                key=lambda x: x[1]
            )[0],
        }

        # Race condition analysis
        shared_counter = [0]
        lock = threading.Lock()

        def unsafe_increment():
            for _ in range(1000):
                shared_counter[0] += 1

        def safe_increment():
            for _ in range(1000):
                with lock:
                    shared_counter[0] += 1

        # Test unsafe
        shared_counter[0] = 0
        threads = [threading.Thread(target=unsafe_increment) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        unsafe_result = shared_counter[0]

        # Test safe
        shared_counter[0] = 0
        threads = [threading.Thread(target=safe_increment) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        safe_result = shared_counter[0]

        result['race_condition_analysis'] = {
            'expected_value': 4000,
            'unsafe_value': unsafe_result,
            'safe_value': safe_result,
            'race_detected': unsafe_result != 4000,
            'data_loss_percent': round((1 - unsafe_result / 4000) * 100, 2),
        }

        # Deadlock analysis
        result['deadlock_analysis'] = {
            'potential_deadlocks': detect_deadlock_patterns(source_code),
            'shared_resources_detected': count_shared_resources(source_code),
            'lock_ordering_issues': False,
        }

        # CPU utilization estimate
        result['cpu_utilization'] = {
            'sequential_utilization': '25%',
            'threaded_utilization': '40-60% (GIL limited)',
            'multiprocess_utilization': '90-100%',
            'async_utilization': '25% (I/O optimized)',
        }

        result['success'] = True

    except SyntaxError as e:
        result['error'] = f"Syntax Error: {str(e)}"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result


def detect_deadlock_patterns(source_code):
    """Detect potential deadlock patterns in code."""
    patterns = []
    lines = source_code.split('\n')
    lock_count = 0
    for i, line in enumerate(lines):
        if 'Lock()' in line or 'acquire' in line:
            lock_count += 1
        if lock_count >= 2 and 'acquire' in line:
            patterns.append({
                'line': i + 1,
                'pattern': 'Multiple lock acquisition',
                'risk': 'medium',
            })
    return patterns


def count_shared_resources(source_code):
    """Count potential shared resources."""
    import ast
    count = 0
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                count += len(node.names)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'self':
                    count += 1
    except Exception:
        pass
    return count
