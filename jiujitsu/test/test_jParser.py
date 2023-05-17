from unittest import TestCase
from jiujitsu import Parser, ParseError, Flag, Arg


class TestjParser(TestCase):
    
    def test_init(self):
        string = '-p run -p echo'
        self.assertRaises(ParseError, Parser, 1234)
        parser = Parser(string)
        self.assertTrue(parser.text == string)
        

    def test_parse(self):
        string = '-fg else "some words" -notaflag'
        parser = Parser()
        flags, args = parser.parse(string)

        self.assertTrue(flags == [Flag('f'), Flag('g')])
        self.assertTrue(args == [Arg('else'), Arg('some words', quoted=True), Arg('-notaflag')])
        self.assertRaises(ParseError, parser.parse, 1234)


    """ This section is now dedicated to parsing edge cases to verify 
        the AST gets built properly and pops errors correctly """
