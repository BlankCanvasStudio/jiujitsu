#!/bin/python3
from jToken import TokenType
from jLexer import Lexer
from jNode import AST, Flag, Arg, Command, Program


""" 
    The AST looks a little something like:

        Program
            commands: 
                [
                    Command
                        flags: [ Flag, Flag, Flag ]
                        args: [ Argument, Argument, Argument ]
                    Command
                        flags: [ Flag, Flag, Flag ]
                        args: [ Argument, Argument, Argument ]
                    Command
                        flags: [ Flag, Flag, Flag ]
                        args: [ Argument, Argument, Argument ]
                ]

    Use Parser.parse(text) to generate an AST. Use the interpreter to do anything with it
"""


class ParseError(Exception):
    pass


class Parser:
    """ Lexer is based around text. Parser processes the text """
    def __init__(self, text, alias_table = None):
        if alias_table is None: alias_table = {}
        if type(text) is not str: raise ParseError("Error Parser(text != string)")
        self.lexer = Lexer(text, alias_table)
        self.current_token = self.get_next_token()


    """ Used to convert the alias table to JSON file so it can be loaded later """
    def json(self):
        return self.lexer.json()


    """ Reset the lexer to the new line. Then you can call parse on it """
    def new(self, text):
        if type(text) is not str: raise ParseError("Parser.new takes a string type object as parameter")
        self.lexer.new(text)
        self.current_token = self.get_next_token()


    """ Nice wrapper so you can use self """
    def get_next_token(self):
        return self.lexer.get_next_token()


    """ Tries to consume type of token_type to verify the parser is encountering the right tokens
        in the correct order. If they don't match a ParseError is raised. Makes for nice reading """
    def eat(self, token_type):
        old_token = self.current_token
        if old_token.type == token_type:
            self.current_token = self.get_next_token()
        else:
            raise ParseError('Parser.eat encountered invalid type: ', token_type)
        return old_token


    """ While there are still nodes left, add a command node to the program node.
        Command nodes contain their respective flags and arguments, think trees & easy 
        interpretation """
    def program(self):
        commands = []
        while str(self.current_token.type) != str(TokenType.EOF):
            commands += [ self.command() ]
            if self.current_token.type is TokenType.EOC:
                self.eat(TokenType.EOC)
        return Program(commands)


    """ Create a command node with the respective flags and arguments """
    def command(self):
        token = self.eat(TokenType.CMD)
        func = token.value
        flags = []
        args = []

        while str(self.current_token.type) == str(TokenType.FLAG):
            flags += [ self.flag() ]        # Use the flag function cause consistency
        while str(self.current_token.type) == str(TokenType.ARG):
            args += [ self.argument() ]     # Use the argument function cause consistency
        return Command(func, flags, args)


    """ How the parser deals with a flag. Eat the flag token and return a flag node """
    def flag(self):
        token = self.eat(TokenType.FLAG)
        return Flag(token.value)


    """ How to create an argument node. Contains only the value. No parts, no lists, nothing. Very simple """
    def argument(self):
        token = self.eat(TokenType.ARG)
        return Arg(token.value, quoted = token.quoted)   # Beautiful


    """ How to use the parse to parse text. If no text is specified, then the last text 
        specified is used (even if that means during declaration) """
    def parse(self, text = None):
        if text is not None: 
            if type(text) is not str: raise ParseError("Parser.parse takes a string object as a parameter")
            self.new(text)     # If you specified new text, use it. Otherwise use previous text
        node = self.program()                   # Create a program node (one per program). Then there should be an EOF
        if self.current_token.type != TokenType.EOF:
            raise ParseError("Error during Parser.parse. EOF node should be encountered but " + str(self.current_token.type) + " was found")
        return node
