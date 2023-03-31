#!/bin/python3
import bashparser
from bpInterpreter import Interpreter

text = open('test.sh').read()
nodes = bashparser.parse(text)
i = Interpreter()
for node in nodes:
    i.run(node)
    i.showState()
