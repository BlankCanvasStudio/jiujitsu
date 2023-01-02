#!/bin/python3
from jInterpreter import Interpreter

"""
from jLexer import Lexer
from jToken import Token, TokenType

lex = Lexer('run \"echo hello world\"')
token = lex.get_next_token()
while token != Token(type_in=TokenType.EOF, value=None):
    print(token)
    token = lex.get_next_token()
"""


cli = Interpreter()
cli.listen()

