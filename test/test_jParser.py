from unittest import TestCase
from jParser import Parser, ParseError
from jToken import Token, TokenType
from jNode import AST, Flag, Arg, Command, Program

class TestjParser(TestCase):
    
    def test_init(self):
        string = 'run echo'
        self.assertRaises(ParseError, Parser, 1234)
        parser = Parser(string)
        self.assertTrue(parser.current_token == Token(TokenType.CMD, 'run'))
        pass

    
    def test_json(self):
        string = 'run else'
        parser = Parser(string)
        self.assertTrue(parser.json() == {})
        parser.lexer.add_alias("some", "run echo")
        expected_results = {
            "some": "run echo"
        }
        self.assertTrue(parser.json() == expected_results)

    
    def test_new(self):
        
        string = 'run else'
        parser = Parser(string)
        parser.lexer.add_alias("some", "run echo")
        parser.new("history -p")
        expected_results = {
            "some": "run echo"
        }
        self.assertTrue(parser.json() == expected_results)
        self.assertTrue(parser.current_token == Token(TokenType.CMD, 'history'))
        self.assertRaises(ParseError, parser.new, 1234)


    def test_eat(self):
        string = 'run else'
        parser = Parser(string)
        self.assertRaises(ParseError, parser.eat, TokenType.ARG)
        self.assertTrue(parser.eat(TokenType.CMD) == Token(TokenType.CMD, 'run'))


    def test_parse(self):
        string = 'run -fg else; fight -hq something;'
        parser = Parser(string)
        program_node = parser.parse()

        cmd1 = Command('run', [Flag('f'), Flag('g')], [Arg('else')])
        cmd2 = Command('fight', [Flag('h'), Flag('q')], [Arg('something')])
        expected_program_node = Program([cmd1, cmd2])
        self.assertTrue(program_node == expected_program_node)
        self.assertRaises(ParseError, parser.parse, 1234)


    """ This section is now dedicated to parsing edge cases to verify 
        the AST gets built properly and pops errors correctly """
