#!/bin/python3
from jToken import Token, TokenType


class LexerError(Exception):
    pass


class Lexer: 
    """ 
    Basic definition of this language:
    command -flags arguments
    only 1 flags section allow, must be proceeded by dash. No double dash shit unless its 
        an argument
    Scripting only, no for loops ?

    This class simply breaks text into tokens, nothing more
    It is the job of the parser to determine if those tokens are in a logical order
    """

    def __init__(self, text, alias_table = None):
        if alias_table is None: alias_table = {}    # Done cause mutable and python might save by reusing the object
        """ I actively hate this so much but python won't give me the raw string. So irritating """
        self.text = text
        self.index = 0
        self.token_index = 0
        self.first_word = True

        """ This is used to hold preprocessed tokens when it makes life easier. 
            Most notably flags are lexed in 1 pass, so you don't need to save any state
            and aliases are saved as tokens to make sure they are valid & so we don't need
            to parse every time """
        self.token_array = []
        
        """ User defined aliases are stored by the judo interpreter here. 
            This means aliases act completely transparently to the parser and makes
            life much easier """
        self.alias_table = alias_table


    """ Converts object to dict so it can be converted to json. __dict__ attr introduced a bug so we use this"""
    def json(self):
        json_alias_table = {}
        for key, value in self.alias_table.items():
            json_alias_table[key] = ' '.join([x.value for x in self.alias_table[key]])
        return json_alias_table


    """ Called whenever you want to lex new text. Easier than making a new lexer every time 
        (cause then you have to also mess with parser) """
    def new(self, text):
        if type(text) is not str: raise LexerError('Lexer.new() can only take string type argument')
        self.__init__(text, self.alias_table)


    """ Returns the current character in the sequence and deals with escape characters """
    def current_char(self, raw = False):
        if type(raw) is not bool: raise LexerError("Argument raw to Lexer.current_char() must be a bool")
        if self.index > len(self.text) - 1: return None
        if self.text[self.index] != '\\' or raw: return self.text[self.index]
        # Now it must be an escaped character so return the actual escaped character in its place
        escaped_char = self.text[self.index + 1]
        if escaped_char == '"':
            return "\"" 
        elif escaped_char == "'":
            return "\'"
        elif escaped_char == 'n':
            return '\n'
        elif escaped_char == 't':
            return '\t'
        elif escaped_char == '\\':
            return '\\'
        else:
            raise LexerError('Unsupported escape character encountered: ' + '\\' + escaped_char)


    """ Increase read pointer in string or set to None when done """
    def advance(self):
        if self.current_char(raw=True) == '\\': self.index = self.index + 1     # skip an escape character
        self.index = self.index + 1


    """ Lexer allows for random whitespace so formatting can look nice """
    def skip_whitespace(self):
        while self.current_char() and self.current_char().isspace():
            self.advance()


    """ How the lexer deals with inline comments:
            Skips until end of line. Assumes that every line is read individually """
    def skip_comment(self):
        while self.current_char() and self.current_char() != '\n':
            self.advance()
        if self.current_char() == '\n': # Skip \n so we start at next line ?
            self.advance()
            self.first_word = True      # New line = new command


    """ Simple wrapper in the event things get more complex """
    def is_alias(self, alias):
        if type(alias) is not str: raise LexerError("Alias passed into Lexer.is_alias must be of type string. \
                                                        \n Type" + str(type(alias)) + ' is invalid')
        return alias in self.alias_table


    """ Takes a command string and name of the new command to create. 
        Saves the resulting tokens in alias_table so we don't need to process them everytime """
    def add_alias(self, name, cmd_aliased):

        if type(name) is not str: raise LexerError("Error occured in Lexer.add_alias. Alias name must be a string")
        if type(cmd_aliased) is not str: raise LexerError("Error occured in Lexer.add_alias. Function to alias must be passed in as string")

        """ Create a temporary lexer with the same alias table to resolve the tokens. 
            This should allow for nested aliasing as it will reduce the aliasing when creating the tokens """
        tmp_lexer = Lexer(cmd_aliased, self.alias_table)

        """ Convert to tokens and save """
        tokens = []
        while tmp_lexer.current_char() is not None:
            tokens += [ tmp_lexer.get_next_token() ]

        self.alias_table[name] = tokens


    """ Checks if string passed in is in alias table. If it is, the tokens of 
        the lexed alias string are shifted onto the front of the tokens array stack to be removed.
        Theoretically the command being aliased is on front of token array so it should be shifted off. """
    def resolve_alias(self, alias):
        if type(alias) is not str: raise LexerError("Error Lexer.resolve_alias takes a single string type argument")
        if self.is_alias(alias):   # ideally the token is on the front of the array so alias needs to be preappended ?
            self.token_array = self.alias_table[alias] + self.token_array
            return self.token_array.pop(0)
        else:
            raise LexerError('Error Occured in Lexer.resolve_alias. Alias passed in not in alias table.')


    """ How the lexer converts the optional flag section into tokens. 
        Tokens after first are then put in the token_array so this can be parsed in 1 pass.
        Avoids annoying state """
    def flags(self):
        self.advance() # shift off the -

        while self.current_char() and not self.current_char().isspace() and (not self.current_char() == ';'):
            self.token_array += [ Token(type_in=TokenType.FLAG, value=self.current_char()) ]
            self.advance()

        return self.token_array.pop(0)


    """ How Lexer deals with semi colons. Makes sure next word is processed as command, not arg, and returns token """
    def EOC(self):
        self.first_word = True
        self.advance()
        return Token(type_in=TokenType.EOC, value=';')


    """ First word of command is parsed. A command can be anything but can't contain spaces. """
    def CMD(self):
        text = ''
        while self.current_char() is not None and not self.current_char().isspace() and (not self.current_char() == ';'):
            text += self.current_char()
            self.advance()
        self.first_word = False
        return Token(type_in=TokenType.CMD, value=text)


    """ How the lexer processes anything that isn't an quoted argument, the flag section, or a command. 
        Can be anything but it can't contain spaces. Words are considered separate arguments, as long as its not quoted """
    def ARG(self):
        text = ''
        while (self.current_char() is not None) and (not self.current_char().isspace()) and (not self.current_char() == ':') and (not self.current_char() == ';'):
            text += self.current_char()
            self.advance()
        return Token(type_in=TokenType.ARG, value=text)


    """ Just like an arg but allows for spaces in it. Terminated by a closing quote, not a space. 
        Raises an error if the quoted argument is not followed by a space or colon """
    def QUOTE(self):
        """ Determine the quote type and shift it off """
        quote_type = self.current_char()
        self.advance()

        text = ''
        while (self.current_char(raw=True) != quote_type):  # Need raw so escaped characters don't pop
            text += self.current_char()
            self.advance()
        self.advance() # Move past final quote

        """ Rasie an error if the quoted argument isn't followed by a space or a colon """
        if self.current_char() and (not self.current_char().isspace() and not self.current_char() == ':'): 
            raise LexerError("Quoted arguments must be followed by a space or colon. Encountered character: " + self.current_char())

        return Token(type_in=TokenType.ARG, value=text, quoted=True)


    """ Called by the parser to get the next token in the sequence """
    def get_next_token(self):

        """ If there are preprocessed tokens, give those rather than reading later tokens.
            Used for flags and aliases currently """
        if len(self.token_array):
            return self.token_array.pop(0)

        """ Determine the token from the text """
        while self.current_char() is not None:

            if self.current_char().isspace():     # Skip white space until we get to next real token. Not raw so \n and \t pop
                self.skip_whitespace()
                continue

            if self.current_char() == '#':        # Skip to end of line if next token start with comment character
                self.advance()
                self.skip_comment()
                continue

            if self.current_char() == '-':        # Flag characters start with a -. No other token types can
                return self.flags()

            if self.current_char() == ';':        # Return an End Of Command token if the start of the next token is a ;
                return self.EOC()

            """ Return an argument with the value of : if one is encountered. 
                Allows for json variable entry with arbitrary spacing """
            if self.current_char() == ':':
                self.advance()
                return Token(type_in=TokenType.ARG, value=':')

            if self.first_word:                                         # If its the first word being read, its the command
                token = self.CMD()
                if self.is_alias(token.value): token = self.resolve_alias(token.value)
                return token
            elif self.current_char(raw=True) == '"' or self.current_char(raw=True) == "'":  # If its a quote, then its a quoted argument so please deal with it
                return self.QUOTE()
            elif self.current_char() is not None:                         # If its not the first char or a quote, then process it like a regular arg
                return self.ARG()

            self.token_index = self.token_index + 1                     # Keep count of the number of tokens processed. Legacy but kept anyway

        return Token(type_in=TokenType.EOF, value=None)                 # If its out of the while loop then its the EOF

    def get_all_tokens(self):
        tokens = [ self.get_next_token() ]
        while tokens[-1] != Token(type_in=TokenType.EOF, value=None):
            tokens += [ self.get_next_token() ]
        return tokens
