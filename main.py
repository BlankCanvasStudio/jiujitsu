import bashparse
from bpInterpreter import Interpreter

text = open('test.sh').read()
nodes = bashparse.parse(text)
i = Interpreter()
for node in nodes:
    i.run(node)
    i.showState()
