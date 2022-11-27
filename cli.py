#!/bin/python3
""" Bringing the death star to a knife fight """

from enum import Enum
import subprocess, os, stat
import bpInterpreter, bashparse

class LexerError(Exception):
    pass

class ParserError(Exception):
    pass

class ErrorCode(Enum):
    UNEXPECTED_TOKEN = 'Unexpected token'
    ID_NOT_FOUND     = 'Identifier not found'
    DUPLICATE_ID     = 'Duplicate id found'

class TokenType(Enum):
    EOF = 'EOF'
    PROGRAM = 'PROGRAM'
    CMD = 'CMD'
    ARG = 'ARG'
    FLAG = "FLAG"
    EOC = 'EOC' # End of Command. Very hacky workaround but whatever

class Token():
    def __init__(self, type, value):
        self.type = type
        self.value = value
    
    def __str__(self):
        print('type: ', self.type)
        print('value: ', self.value)
        return "Token(" + self.type.value + ', value: ', self.value + ')'
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        if type(other) is not Token: return False
        if self.type == other.type and self.value == other.value: return True
        return False


class Lexer: 
    """ 
    Basic definition of this language:
    command -flags arguments
    only 1 flags section allow, must be proceeded by dash. No double dash shit unless its 
        an argument 
    Scripting only, no for loops
    """

    def __init__(self, text):
        self.text = text
        self.index = 0
        self.current_char = self.text[self.index]
        self.first_word = True
        self.in_flags = False

    def error(self):
        raise LexerError("Unknown Lexer Error. Quitting")

    def advance(self):
        self.index = self.index + 1
        if self.index > len(self.text) - 1:
            self.current_char = None
        else:
            self.current_char = self.text[self.index]

    def peek(self):
        peek_index = self.index + 1
        if peek_index > len(self.text) - 1:
            return None
        else:
            return self.text[peek_index]
    
    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def skip_comment(self):
        # Comments act until the end of the line?
        # We said cli only so no block comments?
        while self.current_char is not None:
            self.advance()
    
    def flags(self):
        token = Token(type=TokenType.FLAG, value=None)
        flags_text = ''
        if self.current_char == '-': self.advance()  # Remove the leading -
        
        if self.current_char.isalpha():
            flags_text += self.current_char
            self.advance()

        if self.current_char is None or self.current_char.isspace():
            self.in_flags = False

        token.value = flags_text
        
        return token

    def EOC(self):
        self.first_word = True
        return Token(type=TokenType.EOC, value=';')

    def CMD(self):
        text = ''
        while self.current_char is not None and not self.current_char.isspace():
            text += self.current_char
            self.advance()
        self.first_word = False
        return Token(type=TokenType.CMD, value=text)

    def ARG(self):
        text = ''
        while (self.current_char is not None) and (not self.current_char.isspace()):
            text += self.current_char
            self.advance()
        return Token(type=TokenType.ARG, value=text)

    def get_next_token(self):

        while self.current_char is not None:

            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char == '#':
                self.advance()
                self.skip_comment()
                continue

            if self.current_char == '-':
                self.advance() # Shift off the -
                self.in_flags = True
                continue
            
            if self.in_flags:
                return self.flags()

            if self.current_char == ';':
                return self.EOC()

            if self.first_word:
                return self.CMD()
            elif self.current_char is not None:
                return self.ARG()

        return Token(type=TokenType.EOF, value=None)


def ValidateTypeArray(array, type_in):
    for el in array:
        if type(el) is not type_in:
            raise ParserError()


class AST:
    pass

class Flag(AST):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)
    def __eq__(self, other):
        if type(other) is not Flag: return False 
        return other.value == self.value

class Arg(AST):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)
    def __eq__(self, other):
        if type(other) is not Arg: return False 
        return other.value == self.value

class Command(AST):
    def __init__(self, func, flags, args):
        self.func = func 
        ValidateTypeArray(flags, Flag)
        self.flags = flags
        ValidateTypeArray(args, Arg)
        self.args = args

    def __str__(self):
        return "Command: " \
                + str(self.func) \
                + (' -'+''.join([str(el) for el in self.flags]) if len(self.flags) else '') \
                + ' ' + ' '.join([str(el) for el in self.args])
    
    def __eq__(self, other):    # Man this needs to be cleaner
        if type(other) is not Command: return False 
        if self.func != other.func: return False 
        if len(self.flags) != len(other.flags): return False
        for flag in self.flags: 
            if flag not in other.flags: return False 
        if len(self.args) != len(other.args): return False
        for arg in self.args: 
            if arg not in other.args: return False 
        return True

class Program(AST):
    def __init__(self, commands):
        if type(commands) is not list: commands = [ commands ]
        ValidateTypeArray(commands, Command)
        self.commands = commands

    def __str__(self):
        return "Program \n" +('\n').join( [ '\t'+str(el) for el in self.commands ] )

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.get_next_token()

    def get_next_token(self):
        return self.lexer.get_next_token()

    def error(self, error_code, token):
        print('error code: ', error_code.value)
        print('index: ', self.lexer.index)
        raise ParserError()

    def eat(self, token_type):
        # compare the current token type with the passed token
        # type and if they match then "eat" the current token
        # and assign the next token to the self.current_token,
        # otherwise raise an exception.
        old_token = self.current_token
        if old_token.type == token_type:
            self.current_token = self.get_next_token()
        else:
            print('token type: ', self.current_token.type)
            self.error(
                error_code=ErrorCode.UNEXPECTED_TOKEN,
                token=old_token,
            )
        return old_token

    def flag(self):
        token = self.eat(TokenType.FLAG)
        return Flag(token.value)

    def argument(self):
        return Arg(self.eat(TokenType.ARG).value)   # Beautiful

    def command(self):
        token = self.eat(TokenType.CMD)
        func = token.value
        flags = []
        args = []

        while str(self.current_token.type) == str(TokenType.FLAG):
            flags += [ self.flag() ]
        while str(self.current_token.type) == str(TokenType.ARG):
            args += [ self.argument() ]
        return Command(func, flags, args)

    def program(self):
        commands = []
        while str(self.current_token.type) != str(TokenType.EOF):
            commands += [ self.command() ]
            if self.current_token.type is TokenType.EOC:
                self.eat(TokenType.EOC)
        return Program(commands)

    def parse(self):
        node = self.program()
        if self.current_token.type != TokenType.EOF:
            self.error(
                error_code=ErrorCode.UNEXPECTED_TOKEN,
                token=self.current_token,
            )
        return node


class CLInterpreter:
    def __init__(self):
        self.funcs = {
            'NEXT': self.next, 
            'STATE': self.state, 
            'RUN': self.run,
            'EXIT': self.exit,
            'LOAD': self.load,
        }
        self.env = bpInterpreter.Interpreter()
        self.prog_nodes = None
        self.index = 0
        self.listening = True

    def get_next_node(self):
        if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
        self.index = self.index + 1
        if self.index >= len(self.prog_nodes): return None
        node = self.prog_nodes[self.index]
        return node

    def current_node(self):
        if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
        if self.index >= len(self.prog_nodes): return None
        return self.prog_nodes[self.index]

    def syscall(self, bashCommand):
        tmpFilename = 'tmpFile.sh'
        # Replace all the variables with values in the controlled environment 
        nodes = bashparse.parse(bashCommand)
        replaced_nodes = []
        for node in nodes:
            replaced_nodes += self.env.replace(node)
        # Rewrite it as text
        text = ''
        for node in replaced_nodes:
            text += str(bashparse.NodeVisitor(node)) + '\n'
        # Write a temporary bash file
        fd = open(tmpFilename, 'w')
        fd.write('#!/bin/bash\n'+text)
        fd.close()
        # Make it executable
        st = os.stat(tmpFilename)
        os.chmod(tmpFilename, st.st_mode | stat.S_IEXEC)
        # Call the program & print results
        process = subprocess.Popen('./'+tmpFilename, stdout=subprocess.PIPE) # Execute in the actual environment
        output, error = process.communicate()   # Get the results
        print('Output: ')
        print(output)
        print('Error: ')
        print(error)
        # Delete the temp file
        os.remove(tmpFilename)

    def next(self, flags):
        node = self.get_next_node()
        if Flag('e') in flags: 
            print('here')
            self.syscall(str(bashparse.NodeVisitor(node)))  # Convert to str then syscall
        else: 
            self.env.run(node)
        self.state()

    def state(self, flags = None):
        self.env.showState()

    def run(self, flags, *args):
        text = ''
        for arg in args:
            text += arg.value + ' '
        text = text[:-1]    # last space is wrong plz remove
        if Flag(value='e') in flags: 
            self.syscall(text)
        else:
            print('here')
            nodes = bashparse.parse(text)
            for node in nodes:
                self.env.run(node)

    def exit(self, flags):
        self.listening = False

    def load(self, flags, *args):
        filename = args[0].value
        self.prog_nodes = bashparse.parse(open(filename).read())

    def listen(self):
        print('Welcome to the Judo shell')
        while self.listening:
            cmd = input('> ')
            prog = Parser(Lexer(cmd)).parse()

            for cmd in prog.commands:
                func = self.funcs[cmd.func.upper()]
                func(cmd.flags, *cmd.args)
