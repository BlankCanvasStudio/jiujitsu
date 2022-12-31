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
    def __init__(self, text):
        self.lexer = Lexer(text)
        self.current_token = self.get_next_token()


    """ Reset the lexer to the new line. Then you can call parse on it """
    def new(self, text):
        self.__init__(text)


    """ Nice wrapper so you can use self """
    def get_next_token(self):
        return self.lexer.get_next_token()


    """ Raises an error nicely """
    def error(self, error_code, token):
        raise ParseError('Error code: ' + error_code.value + ' at index: ' + self.lexer.index)


    """ Tries to consume type of token_type to verify the parser is encountering the right tokens
        in the correct order. If they don't match a ParseError is raised. Makes for nice reading """
    def eat(self, token_type):
        old_token = self.current_token
        if old_token.type == token_type:
            self.current_token = self.get_next_token()
        else:
            print('token type: ', self.current_token.type)
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
        return Arg(self.eat(TokenType.ARG).value)   # Beautiful


    """ How to use the parse to parse text. If no text is specified, then the last text 
        specified is used (even if that means during declaration) """
    def parse(self, text = None):
        if text is not None: self.new(text)     # If you specified new text, use it. Otherwise use previous text
        node = self.program()                   # Create a program node (one per program). Then there should be an EOF
        if self.current_token.type != TokenType.EOF:
            raise ParseError("Error during Parser.parse. EOF node should be encountered but " + str(self.current_token.type) + " was found")
        return node
