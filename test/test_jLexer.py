from unittest import TestCase
from jLexer import Lexer, LexerError
from jToken import Token, TokenType

class TestjLexer(TestCase):

    def test_json(self):
        lex = Lexer('some text', {})
        self.assertTrue(lex.json() == {})

        alias_table = {
            't': [ Token(type_in=TokenType.CMD, value='run'), Token(type_in=TokenType.ARG, value='echo'), 
                    Token(type_in=TokenType.ARG, value='hello'), Token(type_in=TokenType.ARG, value='world') ]
            }

        lex = Lexer('some text', alias_table=alias_table)

        expected_results = {
            't':'run echo hello world'
        }
        self.assertTrue(lex.json() == expected_results)


    def test_new(self):
        self.assertRaises(LexerError, Lexer('sometext').new, 1234)
        
        alias_table = {
            't': [ Token(type_in=TokenType.CMD, value='run'), Token(type_in=TokenType.ARG, value='echo'), 
                    Token(type_in=TokenType.ARG, value='hello'), Token(type_in=TokenType.ARG, value='world') ]
            }
        lex = Lexer('text', alias_table=alias_table)
        old_alias_table = lex.alias_table
        lex.new('some newer text')
        self.assertTrue(lex.text == 'some newer text')
        self.assertTrue(lex.index == 0)
        self.assertTrue(lex.first_word == True)
        self.assertTrue(lex.token_array == [])
        self.assertTrue(lex.alias_table == old_alias_table)


    def test_current_char(self):
        self.assertRaises(LexerError, Lexer('some text').current_char, 'anything')
        self.assertRaises(LexerError, Lexer('\s').current_char)
        lex = Lexer(r'')
        self.assertTrue(lex.current_char() is None)
        """ Testing " """
        lex = Lexer(r'\"')
        self.assertTrue(lex.current_char(raw=True) == '\\')
        self.assertTrue(lex.current_char() == '"')
        """ Testing ' """
        lex = Lexer(r"\'")
        self.assertTrue(lex.current_char(raw=True) == '\\')
        self.assertTrue(lex.current_char() == "'")
        """ Testing \n """
        lex = Lexer(r'\n')
        self.assertTrue(lex.current_char(raw=True) == '\\')
        self.assertTrue(lex.current_char() == '\n')
        """ Testing \t """
        lex = Lexer(r'\t')
        self.assertTrue(lex.current_char(raw=True) == '\\')
        self.assertTrue(lex.current_char() == '\t')
        """ Testing \\ """
        lex = Lexer(r'\\')
        self.assertTrue(lex.current_char(raw=True) == '\\')
        self.assertTrue(lex.current_char() == '\\')
        """ Testing no escapes """
        lex = Lexer(r'x')
        self.assertTrue(lex.current_char(raw=True) == 'x')
        self.assertTrue(lex.current_char() == 'x')


    def test_advance(self):
        text = 'some -flg random text'
        lex = Lexer(text)
        for c in text:
            self.assertTrue(lex.current_char() == c)
            lex.advance()
        self.assertTrue(lex.current_char() == None)

        """ Testing advance on escape characters """
        lex = Lexer(r'\t\n')
        self.assertTrue(lex.current_char() == '\t')
        lex.advance()
        self.assertTrue(lex.current_char() == '\n')
        lex.advance()
        self.assertTrue(lex.current_char() == None)

    
    def test_skip_whitepace(self):
        # so technically both are escape characters cause python and judo
        # python makes a big stink about raw vs not raw iteration. If you want \\ not to escape you need to use raw
        text = 's   \\t\\n\t\nome'  
        lex = Lexer(text)
        lex.advance()
        lex.skip_whitespace()
        for c in 'ome':
            self.assertTrue(lex.current_char() == c)
            lex.advance()
    

    def test_skip_comment(self):
        text = "# some comment \nanother command"
        lex = Lexer(text)
        lex.advance()
        lex.skip_comment()
        self.assertTrue(lex.current_char() == 'a')


    def test_is_alias(self):
        self.assertRaises(LexerError, Lexer('some test').is_alias, 1234)
        alias_table = {
            't': [ Token(type_in=TokenType.CMD, value='run'), Token(type_in=TokenType.ARG, value='echo'), 
                    Token(type_in=TokenType.ARG, value='hello'), Token(type_in=TokenType.ARG, value='world') ]
            }

        lex = Lexer('some text', alias_table=alias_table)

        self.assertTrue(lex.is_alias('t'))
        self.assertFalse(lex.is_alias('m'))

        """ Verify test alias works after new """
        lex.new('some more text')
        self.assertTrue(lex.is_alias('t'))
        self.assertFalse(lex.is_alias('m'))


    def test_add_alias(self):
        lex = Lexer('some text')
        self.assertRaises(LexerError, lex.add_alias, 1234, 'something')
        self.assertRaises(LexerError, lex.add_alias, 'something', 1234)

        expected_results = {
            't': [ Token(TokenType.CMD, 'run'), Token(TokenType.ARG, 'this') ]
        }
        lex.add_alias('t', 'run this')
        self.assertTrue(expected_results == lex.alias_table)


    def test_resolve_alias(self):
        alias_table = {
            't': [ Token(type_in=TokenType.CMD, value='run'), Token(type_in=TokenType.ARG, value='echo'), 
                    Token(type_in=TokenType.ARG, value='hello'), Token(type_in=TokenType.ARG, value='world') ]
            }
        lex = Lexer('some text', alias_table=alias_table)
        self.assertRaises(LexerError, lex.resolve_alias, 1234)
        self.assertRaises(LexerError, lex.resolve_alias,'something not in table')
        self.assertTrue(lex.resolve_alias('t') == Token(TokenType.CMD, value='run'))


    """ These tests are dedicated to verifying the high level functionality,
        not the functions themselves. Basically just lexing edge cases """
    def test_flags(self):
        string = "run -fg echo"
        lex = Lexer(string)
        token = lex.get_next_token()
        tokens = [ token ]
        while token != Token(type_in=TokenType.EOF, value=None):
            token = lex.get_next_token()
            tokens += [ token ]
        expected_results = [
            Token(TokenType.CMD, 'run'), Token(TokenType.FLAG, 'f'), Token(TokenType.FLAG, 'g'),
            Token(TokenType.ARG, 'echo'), Token(TokenType.EOF, None)
        ]
        self.assertTrue(expected_results == tokens)


    def test_using_comment(self):
        string = "run -fg echo # something we ignore\nrun -fg echo"
        lex = Lexer(string)
        token = lex.get_next_token()
        tokens = [ token ]
        while token != Token(type_in=TokenType.EOF, value=None):
            token = lex.get_next_token()
            tokens += [ token ]
        expected_results = [
            Token(TokenType.CMD, 'run'), Token(TokenType.FLAG, 'f'), Token(TokenType.FLAG, 'g'),
            Token(TokenType.ARG, 'echo'),
            Token(TokenType.CMD, 'run'), Token(TokenType.FLAG, 'f'), Token(TokenType.FLAG, 'g'),
            Token(TokenType.ARG, 'echo'), Token(TokenType.EOF, None)
        ]
        self.assertTrue(expected_results == tokens)


    def test_using_colon(self):
        string = "run echo:this"
        tokens = Lexer(string).get_all_tokens()
        expected_results = [
            Token(TokenType.CMD, 'run'), Token(TokenType.ARG, 'echo'), Token(TokenType.ARG, ':'), 
            Token(TokenType.ARG, 'this'), Token(TokenType.EOF, None)
        ]
        self.assertTrue(expected_results == tokens)
        
        """ Verify quotes and colons work """
        string = r'run "echo":"this"'
        tokens = Lexer(string).get_all_tokens()
        self.assertTrue(expected_results == tokens)

        """ Veryify spaces and colons work """
        string = "run echo : this"
        tokens = Lexer(string).get_all_tokens()
        self.assertTrue(expected_results == tokens)

        """ Verify quotes, spaces, and colons work """
        string = r'run "echo" : "this"'
        tokens = Lexer(string).get_all_tokens()
        self.assertTrue(expected_results == tokens)


    def test_using_semicolon(self):
        string = "run echo this; run echo"
        tokens = Lexer(string).get_all_tokens()
        expected_results = [
            Token(TokenType.CMD, 'run'), Token(TokenType.ARG, 'echo'), 
            Token(TokenType.ARG, 'this'), Token(TokenType.EOC, ';'), 
            Token(TokenType.CMD, 'run'), Token(TokenType.ARG, 'echo'), 
            Token(TokenType.EOF, None)
        ]
        self.assertTrue(expected_results == tokens)


    def test_using_quotes(self):
        string = r'run "echo this"'
        tokens = Lexer(string).get_all_tokens()
        expected_results = [
            Token(TokenType.CMD, 'run'), Token(TokenType.ARG, 'echo this'), 
            Token(TokenType.EOF, None)
        ]
        self.assertTrue(expected_results == tokens)
