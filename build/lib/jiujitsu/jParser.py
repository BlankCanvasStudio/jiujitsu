from jiujitsu.jNode import Flag, Arg


class ParseError(Exception):
    pass


""" CMD wraps a weird amount of parsing so moving away from proper AST language implementation
    and combining parser and lexer into single step cause its easier and maves development simpler :'( """
class Parser():
    def __init__(self, text = ''):
        if type(text) is not str: raise ParseError("jParser.text must be of type string")
        self.text = text
        self.index = 0


    """ Increase read pointer in string or set to None when done """
    def advance(self):
        # if self.current_char() == '\\': self.index = self.index + 1     # skip an escape character
        self.index = self.index + 1


    """ Lexer allows for random whitespace so formatting can look nice """
    def skip_whitespace(self):
        while self.current_char() and self.current_char().isspace():
            self.advance()


    """ Returns an escaped character. Used in quote to prevent accidental escaping """
    def escape_char(self):
        escaped_char = None
        self.advance()  # remove the \ from the escaped character
        if self.current_char() == 'n':
            escaped_char = '\n'
        elif self.current_char() == 't':
            escaped_char = '\t'
        elif self.current_char() == '\\':
            escaped_char = '\\'
        elif self.current_char() == '"':
            escaped_char = '"'
        elif self.current_char() == "'":
            escaped_char = "'"
        else:
            raise ParseError('Unknown escape character encountered: \\', + self.current_char())

        return escaped_char



    """ How the lexer processes anything that isn't an quoted argument, the flag section, or a command. 
        Can be anything but it can't contain spaces. Words are considered separate arguments, as long as its not quoted """
    def ARG(self):
        text = ''
        while (self.current_char() is not None) and (not self.current_char().isspace()) and (not self.current_char() == ':'):
            if self.current_char() == '\\': 
                text += self.escape_char()
            else: 
                text += self.current_char()
            self.advance()
        return Arg(text)

    
    """ Just like an arg but allows for spaces in it. Terminated by a closing quote, not a space. 
        Raises an error if the quoted argument is not followed by a space or colon """
    def QUOTE(self):
        """ Determine the quote type and shift it off """
        quote_type = self.current_char()
        self.advance()

        text = ''
        while (self.current_char() != quote_type):
            if self.current_char() == '\\': 
                text += self.escape_char()
            else: 
                text += self.current_char()
            
            self.advance()
        self.advance() # Move past final quote

        """ Rasie an error if the quoted argument isn't followed by a space or a colon """
        if self.current_char() and (not self.current_char().isspace() and not self.current_char() == ':'): 
            raise ParseError("Quoted arguments must be followed by a space or colon. Encountered character: " + self.current_char())

        return Arg(value=text, quoted=True)


    def current_char(self):
        if self.index > len(self.text) - 1: return None
        return self.text[self.index]


    def flags(self):
        self.advance() # shift off the -

        flags = []

        if self.current_char() and self.current_char().isspace():
            self.skip_whitespace()

        while self.current_char() and not self.current_char().isspace() and (not self.current_char() == ';'):
            flags += [ Flag(self.current_char()) ]
            self.advance()

        return flags


    def args(self):

        args = []

        while self.current_char() is not None:

            if self.current_char().isspace():
                self.skip_whitespace()
                continue

            if self.current_char() == '#':        # Skip to end of line if next token start with comment character
                self.advance()
                self.skip_comment()
                continue                    

            if self.current_char() == ':':
                self.advance()
                args += [ Arg(value=':') ]

            elif self.current_char() == '"' or self.current_char() == "'":  # If its a quote, then its a quoted argument so please deal with it
                args += [ self.QUOTE() ]
            
            elif self.current_char() is not None:                         # If its not the first char or a quote, then process it like a regular arg
                args += [ self.ARG() ]

        return args


    def skip_comment(self):
        while self.current_char() and self.current_char() != '\n':
            self.advance()
        if self.current_char() == '\n': # Skip \n so we start at next line ?
            self.advance()


    def parse(self, text):
        self.__init__(text)
        
        flags = []
        if self.current_char() == '-':
            flags = self.flags()
        args = self.args()
    
        return flags, args
        

