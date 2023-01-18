#!/bin/python3
"""Load a bash interpreter to allow safe analysis of bash scripts"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
from logging import debug, info, warning, error, critical
from jNode import Arg
import logging
import sys

from jInterpreter import Interpreter

def parse_args():
    "Parse the command line arguments."
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                            description=__doc__,
                            epilog="Exmaple Usage: ")

    parser.add_argument("--log-level", "--ll", default="info",
                        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).")

    parser.add_argument("input_script", nargs='?', default=None,
                        help="Initial script to load")

    args = parser.parse_args()
    log_level = args.log_level.upper()
    logging.basicConfig(level=log_level,
                        format="%(levelname)-10s:\t%(message)s")
    return args


def main():
    args = parse_args()

    cli = Interpreter()
    if args.input_script:
        cli.load([], Arg(args.input_script))
    cli.listen()



if __name__ == "__main__":
    main()



# helpful example text
"""
from jLexer import Lexer
from jToken import Token, TokenType

lex = Lexer('run \"echo hello world\"')
token = lex.get_next_token()
while token != Token(type_in=TokenType.EOF, value=None):
    print(token)
    token = lex.get_next_token()
"""

