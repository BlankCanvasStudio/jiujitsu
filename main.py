from tinyCompiler import PythonParser, Compiler

# parser = PythonParser('interpreter.py')

compiler = Compiler(parser_filename='/home/adam/GitHub/bashlex/bashlex/parser.py', interpreter_filename='interpreter.py', output_filename='judo/parser.py')
compiler.build()

import sys
# caution: path[0] is reserved for script path (or '' in REPL)
sys.path.insert(1, '/home/adam/GitHub/judo/judo/')

import parser as bashlex

nodes = bashlex.parse("echo something else | echo that | echo this")

for node in nodes:
    print(node.dump())
# print(parser.dump())
