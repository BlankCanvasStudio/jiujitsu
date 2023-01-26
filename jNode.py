#!/bin/python3
""" Define all the nodes used in the Judo AST """
class AST:
    pass


class Flag(AST):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "Flag{" + str(self.value) + "}"
    def __repr__(self):
        return self.__str__()
    def __eq__(self, other):
        if type(other) is not Flag: return False 
        return other.value == self.value


class Arg(AST):
    def __init__(self, value, quoted = False):
        self.value = value
        self.quoted = quoted
    def __str__(self):
        return "Arg{" + str(self.value) + "}"
    def __repr__(self):
        return self.__str__()
    def __eq__(self, other):
        if type(other) is not Arg: return False 
        return other.value == self.value
    def unescape(self):
        text = self.value.replace('\\', "\\\\").replace('\"', "\\\"").replace('\t', '\\t').replace('\n', '\\n')
        if self.quoted: text = '"' + text + '"'
        return text


class Command(AST):
    def __init__(self, func, flags, args):
        self.func = func 
        for el in flags:
            if type(el) is not Flag: raise ParserError()
        self.flags = flags
        for el in args:
            if type(el) is not Arg: raise ParserError()
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
    
    def __repr__(self):
        return self.__str__()


class Program(AST):
    def __init__(self, commands):
        if type(commands) is not list: commands = [ commands ]
        for el in commands:
            if type(el) is not Command: raise ParserError()
        self.commands = commands

    def __str__(self):
        return "Program \n" +('\n').join( [ '\t'+str(el) for el in self.commands ] )
    
    def __eq__(self, other):
        if len(self.commands) != len(other.commands): return False
        for i in range(0, len(self.commands)):
            if self.commands[i] != other.commands[i]: return False
        return True