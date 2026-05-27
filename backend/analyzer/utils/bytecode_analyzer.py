"""Bytecode compilation analysis utilities."""
import dis
import io
import sys
import time
import types
from collections import Counter


def analyze_bytecode(source_code):
    """Compile source code and extract bytecode information."""
    result = {
        'success': False,
        'bytecode_instructions': [],
        'opcode_frequency': {},
        'total_instructions': 0,
        'compilation_time': 0,
        'execution_comparison': {},
        'raw_bytecode': '',
        'constants': [],
        'names': [],
        'error': None,
    }

    try:
        start_compile = time.perf_counter()
        code_obj = compile(source_code, '<user_input>', 'exec')
        compilation_time = (time.perf_counter() - start_compile) * 1000

        result['compilation_time'] = round(compilation_time, 4)

        # Capture dis output
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        dis.dis(code_obj)
        sys.stdout = old_stdout
        result['raw_bytecode'] = buffer.getvalue()

        # Parse instructions
        instructions = list(dis.get_instructions(code_obj))
        opcode_counter = Counter()

        for instr in instructions:
            result['bytecode_instructions'].append({
                'offset': instr.offset,
                'opname': instr.opname,
                'opcode': instr.opcode,
                'arg': instr.arg if instr.arg is not None else '',
                'argval': str(instr.argval) if instr.argval is not None else '',
                'line': getattr(instr, 'starts_line', None) or getattr(instr, 'line_number', '') or '',
            })
            opcode_counter[instr.opname] += 1

        result['opcode_frequency'] = dict(opcode_counter.most_common(20))
        result['total_instructions'] = len(instructions)

        # Extract constants and names
        result['constants'] = [str(c) for c in code_obj.co_consts if not isinstance(c, types.CodeType)]
        result['names'] = list(code_obj.co_names)

        # Execution comparison
        start_interpreted = time.perf_counter()
        try:
            exec(source_code, {'__builtins__': __builtins__}, {})
        except Exception:
            pass
        interpreted_time = (time.perf_counter() - start_interpreted) * 1000

        start_compiled = time.perf_counter()
        try:
            exec(code_obj, {'__builtins__': __builtins__}, {})
        except Exception:
            pass
        compiled_time = (time.perf_counter() - start_compiled) * 1000

        result['execution_comparison'] = {
            'interpreted_ms': round(interpreted_time, 4),
            'compiled_ms': round(compiled_time, 4),
            'speedup': round(interpreted_time / max(compiled_time, 0.0001), 2),
        }

        result['success'] = True

    except SyntaxError as e:
        result['error'] = f"Syntax Error: {str(e)}"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result


def get_nested_bytecode(source_code):
    """Get bytecode for nested functions/classes."""
    nested = []
    try:
        code_obj = compile(source_code, '<user_input>', 'exec')
        for const in code_obj.co_consts:
            if isinstance(const, types.CodeType):
                old_stdout = sys.stdout
                sys.stdout = buffer = io.StringIO()
                dis.dis(const)
                sys.stdout = old_stdout
                nested.append({
                    'name': const.co_name,
                    'bytecode': buffer.getvalue(),
                    'instruction_count': len(list(dis.get_instructions(const))),
                })
    except Exception:
        pass
    return nested
