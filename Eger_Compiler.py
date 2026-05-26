import sys
import os
import re
import math
import random
import time
import datetime
import traceback

def eger_type(obj):
    if isinstance(obj, bool): return "Type : 'Boolean'"
    elif isinstance(obj, int): return "Type : 'Integer'"
    elif isinstance(obj, float): return "Type : 'Decimal'"
    elif isinstance(obj, str): return "Type : 'String'"
    elif isinstance(obj, list): return "Type : 'Box'"
    elif isinstance(obj, dict): return "Type : 'Note'"
    elif isinstance(obj, set): return "Type : 'Set'"
    elif isinstance(obj, tuple): return "Type : 'pit'"
    return f"Type : '{type(obj).__name__}'"

class EgerTestCompiler:
    def __init__(self):
        self.keywords = {'fnc', 'try', 'flag', 'raise_flag', '#call', 'if', 'else', 'elif', 'while', 'for', 'break', 'continue', 'skip'}
        self.envelop_mode = None
        self.current_phase = "HEADER"  # Phases: HEADER -> LIBRARY -> BODY
        self.imported_libraries = set()

        # Core Built-in Library Functions Mapping
        self.library_registry = {
            'timestamp_now': 'time',
            'datestamp_today': 'date',
            'add': 'math', 'sub': 'math', 'mul': 'math', 'div': 'math', 
            'percentage': 'math', 'random': 'math', 'sqrt': 'math',
            'datetime': 'datetime',
            'write': 'stdio', 'read': 'stdio',
            'int': 'typecast', 'dec': 'typecast', 'bol': 'typecast', 'str': 'typecast', 'type': 'typecast'
        }

        # Execution Environment Context
        self.env = {
            'type': eger_type,
            'write': print,
            'read': input,
            'int': int,
            'dec': float,
            'bol': bool,
            'str': str,
            'add': lambda v1, v2: v1 + v2,
            'sub': lambda v1, v2: v1 - v2,
            'mul': lambda v1, v2: v1 * v2,
            'div': lambda v1, v2: v1 / v2,
            'percentage': lambda v1, v2: (v1 / v2) * 100 if v2 != 0 else 0,
            'random': lambda x: random.choice(x) if isinstance(x, list) else random.random(),
            'sqrt': math.sqrt,
            'datetime': lambda: datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
            'datestamp_today': lambda: datetime.datetime.now().strftime('%d-%m-%Y'),
            'timestamp_now': lambda: time.time(),
        }

    def verify_comment_rules(self, line: str):
        stripped = line.strip()
        if '--' in stripped:
            if re.search(r'-{4,}', stripped) or not (stripped.startswith('---') and stripped.endswith('---')):
                raise SyntaxError("SYNTAX_ERROR: Invalid Comment Style")
            return True
        return False

    def validate_library_calls(self, code_part: str):
        """Checks if a library-dependent function is used without an explicit #call import statement."""
        for func, lib in self.library_registry.items():
            if re.search(r'\b' + re.escape(func) + r'\s*\(', code_part):
                if lib not in self.imported_libraries:
                    raise SyntaxError(f"SYNTAX_ERROR: Function '{func}()' requires library '{lib}' to be explicitly called.")

    def transform_line(self, line: str, is_repl: bool = False) -> str:
        code_part_only = line.lstrip(' \t')
        test_part_code = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '', code_part_only)
        
        # Error check for spacing rules and invalid stacked operators
        if re.search(r' {4,}', test_part_code):
            raise SyntaxError("SYNTAX_ERROR: More Spaces than permitted (Max 3 continuous spaces)")
        if '++' in test_part_code or '--' in test_part_code:
            raise SyntaxError("SYNTAX_ERROR: Invalid operator syntax")

        stripped = line.strip()
        if not stripped:
            return line

        # Parse Comments
        if self.verify_comment_rules(line):
            content = stripped.strip('-').strip()
            return line.replace(stripped, f"# {content}")

        # Parse Header Phase
        if stripped.startswith('Envelop:'):
            if not is_repl and self.current_phase != "HEADER":
                raise SyntaxError("SYNTAX_ERROR: Envelop specification must be at the absolute top of Header Section")
            
            match = re.match(r'^Envelop:\s*"([^"]+)"', stripped)
            if match and match.group(1) == "script":
                self.envelop_mode = "script"
                if not is_repl:
                    self.current_phase = "LIBRARY"
                return "# [Target Profile Locked: SCRIPT]"
            else:
                raise SyntaxError("SYNTAX_ERROR: Invalid Envelop target. This engine only supports Envelop:\"script\"")

        # Parse Library Import Phase
        if stripped.startswith('#call'):
            if not is_repl:
                if self.current_phase == "HEADER":
                    raise SyntaxError("SYNTAX_ERROR: Missing Envelop specification before calling libraries")
                if self.current_phase == "BODY":
                    raise SyntaxError("SYNTAX_ERROR: Library import declarations must be placed before the code body code")
                self.current_phase = "LIBRARY"
            
            match = re.match(r'^#call\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
            if match:
                lib_name = match.group(1)
                valid_libs = {'time', 'date', 'math', 'datetime', 'stdio', 'typecast'}
                if lib_name not in valid_libs:
                    raise SyntaxError(f"SYNTAX_ERROR: Library '{lib_name}' does not exist")
                self.imported_libraries.add(lib_name)
                return f"# [Library Activated: {lib_name}]"
            raise SyntaxError("SYNTAX_ERROR: Invalid library call syntax structural pattern")

        # Handle Phase transitions for non-repl files
        if not is_repl:
            if self.current_phase == "HEADER":
                raise SyntaxError("SYNTAX_ERROR: Missing Envelop specification in Header Section")
            self.current_phase = "BODY"
        else:
            if not self.envelop_mode:
                self.envelop_mode = "script"
                # Interactive mode defaults libraries for rapid student execution experiments
                self.imported_libraries.update(['time', 'date', 'math', 'datetime', 'stdio', 'typecast'])

        leading_whitespace = line[:len(line) - len(line.lstrip())]
        code_part = line[len(line) - len(line.lstrip()):]

        if "'" in code_part or "input(" in code_part:
            raise SyntaxError("SYNTAX_ERROR: Invalid string symbol or internal call token detected")

        # Validate structured inclusions
        self.validate_library_calls(code_part)

        # 3-Part Custom Slicing Correction Mapping [start:interval:end] -> [start:end:interval]
        code_part = re.sub(r'\[([^:\t\n\]]*):([^:\t\n\]]*):([^:\t\n\]]*)\]', r'[\1:\3:\2]', code_part)

        # Convert Grammar Keywords to Interpreter Equivalents
        code_part = re.sub(r'\bskip\b', 'pass', code_part)
        code_part = re.sub(r'\bfnc\b', 'def', code_part)
        code_part = re.sub(r'\bflag:\s*$', 'except Exception:', code_part)
        code_part = re.sub(r'\braise_flag:\s*$', 'if True:', code_part)
        code_part = re.sub(r'\bdec\b(?=\s*\()', 'float', code_part)
        code_part = re.sub(r'\bbol\b(?=\s*\()', 'bool', code_part)

        return leading_whitespace + code_part

    def execute_source(self, eger_code: str, is_repl: bool = False):
        if not is_repl:
            self.envelop_mode = None
            self.current_phase = "HEADER"
            self.imported_libraries.clear()

        # Zero Division Rule Check
        for idx, line in enumerate(eger_code.splitlines(), 1):
            if re.search(r'/\s*0(?:\.0+)?(?!\d)', line):
                print(f"Error on line {idx}: RUNTIME_ERROR: Division by zero") if not is_repl else print("RUNTIME_ERROR: Division by zero")
                return

        python_lines = []
        for idx, line in enumerate(eger_code.splitlines(), 1):
            try:
                python_lines.append(self.transform_line(line, is_repl=is_repl))
            except SyntaxError as e:
                print(f"Error on line {idx}: {str(e)}") if not is_repl else print(str(e))
                return

        if not self.envelop_mode:
            print("SYNTAX_ERROR: Missing Envelop specification ('Envelop:\"script\"')")
            return

        compiled_py = "\n".join(python_lines)
        
        try:
            if is_repl:
                try:
                    res = eval(compiled_py, globals(), self.env)
                    if res is not None:
                        print(f'"{res}"' if isinstance(res, str) else res)
                except SyntaxError:
                    exec(compiled_py, globals(), self.env)
            else:
                exec(compiled_py, globals(), self.env)
        except Exception as e:
            if isinstance(e, AttributeError):
                details = "RUNTIME_ERROR: Invalid variable declaration"
            elif isinstance(e, NameError):
                details = "RUNTIME_ERROR: Variable not defined"
            elif isinstance(e, ZeroDivisionError):
                details = "RUNTIME_ERROR: Division by zero"
            elif isinstance(e, SyntaxError):
                details = "SYNTAX_ERROR: Invalid syntax structure"
            else:
                details = str(e)
            
            if is_repl:
                print(details)
            else:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.extract_tb(exc_traceback)
                line_num = tb[-1].lineno if tb else 1
                print(f"Error on line {line_num}: {details}")

def start_engine_runtime():
    engine = EgerTestCompiler()
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if not filename.endswith(".egr"):
            print("Unsupported file format. Only .egr files are supported.")
            sys.exit(0)
            
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read().lstrip('\ufeff')  
            engine.execute_source(source, is_repl=False)
        else:
            print(f"Error: File '{filename}' not found.")
        sys.exit(0)

    print("Welcome to Eger Language Engine Runtime [Test Profile]")
    
    while True:
        try:
            command = input("Eger> ")
            cmd_clean = command.strip()
            if not cmd_clean: continue
            
            if cmd_clean.startswith('sm ') or cmd_clean == 'sm':
                print("SYNTAX_ERROR: Invalid command")
                continue

            if cmd_clean.endswith('.egr') and ' ' not in cmd_clean:
                if os.path.exists(cmd_clean):
                    with open(cmd_clean, 'r', encoding='utf-8') as f:
                        source = f.read().lstrip('\ufeff')  
                    engine.execute_source(source, is_repl=False)
                else:
                    print("Error: File not found.")
                continue
            
            if any(token.endswith('.egr') for token in cmd_clean.split()):
                print("SYNTAX_ERROR: Invalid command")
                continue
            
            engine.execute_source(command, is_repl=True)
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Eger Engine Runtime.")
            sys.exit(0)

if __name__ == "__main__":
    start_engine_runtime()