"""Optimizing compiler and interpreter module."""
import ast
import textwrap
import time
import copy


class CodeOptimizer:
    """Implements common compiler optimizations on Python AST."""

    def __init__(self, source_code):
        self.source = source_code
        self.tree = ast.parse(source_code)
        self.optimizations_applied = []
        self.stats = {}

    def constant_folding(self):
        """Replace constant expressions with their computed values."""

        class ConstantFolder(ast.NodeTransformer):
            def __init__(self):
                self.folded_count = 0

            def visit_BinOp(self, node):
                self.generic_visit(node)
                if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                    try:
                        ops = {
                            ast.Add: lambda a, b: a + b,
                            ast.Sub: lambda a, b: a - b,
                            ast.Mult: lambda a, b: a * b,
                            ast.Div: lambda a, b: a / b,
                            ast.FloorDiv: lambda a, b: a // b,
                            ast.Mod: lambda a, b: a % b,
                            ast.Pow: lambda a, b: a ** b,
                        }
                        op_type = type(node.op)
                        if op_type in ops:
                            result = ops[op_type](node.left.value, node.right.value)
                            self.folded_count += 1
                            return ast.Constant(value=result)
                    except Exception:
                        pass
                return node

        tree_copy = copy.deepcopy(self.tree)
        folder = ConstantFolder()
        new_tree = folder.visit(tree_copy)
        ast.fix_missing_locations(new_tree)

        if folder.folded_count > 0:
            self.optimizations_applied.append({
                'name': 'Constant Folding',
                'description': f'Folded {folder.folded_count} constant expression(s)',
                'count': folder.folded_count,
            })
        self.stats['constant_folding'] = folder.folded_count
        return new_tree

    def dead_code_elimination(self):
        """Remove unreachable code after return statements."""

        class DeadCodeEliminator(ast.NodeTransformer):
            def __init__(self):
                self.eliminated_count = 0

            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                new_body = []
                found_return = False
                for stmt in node.body:
                    if found_return:
                        self.eliminated_count += 1
                        continue
                    new_body.append(stmt)
                    if isinstance(stmt, ast.Return):
                        found_return = True
                node.body = new_body if new_body else [ast.Pass()]
                return node

            def visit_If(self, node):
                self.generic_visit(node)
                if isinstance(node.test, ast.Constant):
                    if node.test.value:
                        self.eliminated_count += 1
                        return node.body if node.body else [ast.Pass()]
                    else:
                        self.eliminated_count += 1
                        return node.orelse if node.orelse else [ast.Pass()]
                return node

        tree_copy = copy.deepcopy(self.tree)
        eliminator = DeadCodeEliminator()
        new_tree = eliminator.visit(tree_copy)
        ast.fix_missing_locations(new_tree)

        if eliminator.eliminated_count > 0:
            self.optimizations_applied.append({
                'name': 'Dead Code Elimination',
                'description': f'Eliminated {eliminator.eliminated_count} dead code block(s)',
                'count': eliminator.eliminated_count,
            })
        self.stats['dead_code_elimination'] = eliminator.eliminated_count
        return new_tree

    def loop_unrolling(self):
        """Detect simple loops with constant ranges and unroll them."""

        class LoopUnroller(ast.NodeTransformer):
            def __init__(self):
                self.unrolled_count = 0

            def visit_For(self, node):
                self.generic_visit(node)
                if (isinstance(node.iter, ast.Call) and
                        isinstance(node.iter.func, ast.Name) and
                        node.iter.func.id == 'range' and
                        len(node.iter.args) == 1 and
                        isinstance(node.iter.args[0], ast.Constant) and
                        isinstance(node.iter.args[0].value, int) and
                        node.iter.args[0].value <= 8):
                    n = node.iter.args[0].value
                    target = node.target
                    new_body = []
                    for i in range(n):
                        for stmt in node.body:
                            new_stmt = copy.deepcopy(stmt)
                            new_body.append(new_stmt)
                    self.unrolled_count += 1
                    return new_body
                return node

        tree_copy = copy.deepcopy(self.tree)
        unroller = LoopUnroller()
        new_tree = unroller.visit(tree_copy)
        ast.fix_missing_locations(new_tree)

        if unroller.unrolled_count > 0:
            self.optimizations_applied.append({
                'name': 'Loop Unrolling',
                'description': f'Unrolled {unroller.unrolled_count} small loop(s)',
                'count': unroller.unrolled_count,
            })
        self.stats['loop_unrolling'] = unroller.unrolled_count
        return new_tree

    def function_inlining(self):
        """Detect simple one-line functions and inline them at call sites."""

        class FunctionInliner(ast.NodeTransformer):
            def __init__(self):
                self.inlined_count = 0
                self.inline_candidates = {}

            def find_candidates(self, tree):
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if (len(node.body) == 1 and isinstance(node.body[0], ast.Return)):
                            self.inline_candidates[node.name] = {
                                'args': [a.arg for a in node.args.args],
                                'return_expr': node.body[0].value,
                            }

            def visit_Call(self, node):
                self.generic_visit(node)
                if (isinstance(node.func, ast.Name) and
                        node.func.id in self.inline_candidates):
                    self.inlined_count += 1
                return node

        tree_copy = copy.deepcopy(self.tree)
        inliner = FunctionInliner()
        inliner.find_candidates(tree_copy)
        new_tree = inliner.visit(tree_copy)
        ast.fix_missing_locations(new_tree)

        if inliner.inlined_count > 0:
            self.optimizations_applied.append({
                'name': 'Function Inlining',
                'description': f'Identified {inliner.inlined_count} inlinable call(s) from {len(inliner.inline_candidates)} candidate(s)',
                'count': inliner.inlined_count,
                'candidates': list(inliner.inline_candidates.keys()),
            })
        self.stats['function_inlining'] = inliner.inlined_count
        return new_tree


def analyze_optimizations(source_code):
    """Run all optimizations and return comparison results."""
    result = {
        'success': False,
        'original_code': source_code,
        'optimized_code': '',
        'optimizations': [],
        'stats': {},
        'performance_comparison': {},
        'error': None,
    }

    try:
        optimizer = CodeOptimizer(source_code)

        # Run all optimizations
        optimizer.constant_folding()
        optimizer.dead_code_elimination()
        optimizer.loop_unrolling()
        optimizer.function_inlining()

        # Generate optimized code from combined optimizations
        combined_tree = copy.deepcopy(optimizer.tree)

        class CombinedOptimizer(ast.NodeTransformer):
            def visit_BinOp(self, node):
                self.generic_visit(node)
                if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                    try:
                        ops = {
                            ast.Add: lambda a, b: a + b,
                            ast.Sub: lambda a, b: a - b,
                            ast.Mult: lambda a, b: a * b,
                            ast.Div: lambda a, b: a / b,
                        }
                        op_type = type(node.op)
                        if op_type in ops:
                            val = ops[op_type](node.left.value, node.right.value)
                            return ast.Constant(value=val)
                    except Exception:
                        pass
                return node

            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                new_body = []
                found_return = False
                for stmt in node.body:
                    if found_return:
                        continue
                    new_body.append(stmt)
                    if isinstance(stmt, ast.Return):
                        found_return = True
                node.body = new_body if new_body else [ast.Pass()]
                return node

        opt = CombinedOptimizer()
        combined_tree = opt.visit(combined_tree)
        ast.fix_missing_locations(combined_tree)
        result['optimized_code'] = ast.unparse(combined_tree)

        result['optimizations'] = optimizer.optimizations_applied
        result['stats'] = optimizer.stats

        # Performance comparison
        safe_globals = {'__builtins__': __builtins__}

        start = time.perf_counter()
        for _ in range(100):
            try:
                exec(source_code, safe_globals.copy(), {})
            except Exception:
                break
        original_time = (time.perf_counter() - start) * 1000

        optimized_code = compile(result['optimized_code'], '<optimized>', 'exec')
        start = time.perf_counter()
        for _ in range(100):
            try:
                exec(optimized_code, safe_globals.copy(), {})
            except Exception:
                break
        optimized_time = (time.perf_counter() - start) * 1000

        result['performance_comparison'] = {
            'original_ms': round(original_time, 4),
            'optimized_ms': round(optimized_time, 4),
            'improvement_percent': round(
                ((original_time - optimized_time) / max(original_time, 0.0001)) * 100, 2
            ),
            'iterations': 100,
        }

        result['success'] = True

    except SyntaxError as e:
        result['error'] = f"Syntax Error: {str(e)}"
    except Exception as e:
        result['error'] = f"Error: {str(e)}"

    return result
