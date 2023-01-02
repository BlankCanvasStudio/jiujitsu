#!/bin/python3
from enum import Enum


""" All the tokens allowed in the judo language """
class TokenType(Enum):
    EOF = 'EOF'
    PROGRAM = 'PROGRAM'
    CMD = 'CMD'
    ARG = 'ARG'
    FLAG = 'FLAG'
    EOC = 'EOC' # End of Command. Very hacky workaround but whatever


""" Simple Token class that lexer returns to the parser """
class Token():
    def __init__(self, type_in, value):
        self.type = type_in
        self.value = value
    
    def __str__(self):
        return "Token(" + self.type.value + ', value: ' + (self.value or 'None') + ')'
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        if type(other) is not Token: return False
        if self.type == other.type and self.value == other.value: return True
        return False
