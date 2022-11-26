#!/bin/bash

import bashparse, copy, validators
from bashparse import NodeVisitor


class FileSocket:
    def __init__(self, id_num, working_dir = '~'):
        self.OUT = ''
        self.id = id_num
        self.IN = ''

    def write(self, text_in):
        self.OUT += text_in 

    def read(self):
        tmp = self.IN
        self.IN = ''
        return tmp

    def transfer(self):
        self.IN = self.OUT
        self.OUT = ''


class File:
    def __init__(self, name, contents, permissions = 'rw-rw-rw-'):
        self.name = name
        self.contents = contents
        self.permissions = permissions

    def __str__(self):
        print('FileName: ', self.name)
        print('  Permissions: ', self.permissions)
        print('  Contents: ', self.contents)
    
    def setPermissions(self, permissions):
        self.permissions = permissions


class InterpreterBase():

    def __init__(self, working_dir = '~'):
        self.STDIO = FileSocket(id_num = 0)
        self.working_dir = working_dir
        self.variables = {'sshports':['one', 'two']}
        self.fs = {}
        self.open_sockets = []
        self.bin = []
        self.truths = {}
        method_list = [ func for func in dir(Interpreter) if callable(getattr(Interpreter, func)) ]
        for method in method_list:
            if method[:2] == 'f_':
                self.bin += [ method[2:] ]


    def showState(self, showFiles = False):
        print('Interpreter State: ')
        print('Working directory: ', self.working_dir)
        print('Variables: ')
        for key, value in self.variables.items():
            print('  ' + key + ': ' + value[-1])
        print('Number of open sockets: ', len(self.open_sockets))
        print('Standard IN: ', self.STDIO.IN)
        print('Standard OUT: ', self.STDIO.OUT)
        print('File System: ')
        for name, file in self.fs.items():
            print('  ' + name + ' permissions: ' + str(file.permissions))
            if showFiles:
                print(file.contents)


    def interpreter(self, node, vstr):
        if node.kind == 'pipeline':
            for i, part in enumerate(node.parts):
                if i % 2 != 0:
                    self.STDIO.transfer()
                else:
                    vstr2 = NodeVisitor(part)
                    self.interpreter(part, vstr2)
        
        elif node.kind == 'command':
            self.run_command(node.parts[0], node.parts[1:])
        
        elif node.kind == 'list':
            previous_result = None
            execute = True
            for i, part in enumerate(node.parts):
                if i % 2 == 0:
                    if execute:
                        vstr2 = NodeVisitor(part)
                        self.interpreter(part, vstr2)
                        self.STDIO.transfer()
                        previous_result = self.STDIO.read()
                else:
                    if part.op == '||':
                        if previous_result.isnumeric() and int(previous_result) == 0:        # Rest are execute iff last aprt has non-zero return value
                            execute = False
                    elif part.op == '&&':  
                        if previous_result.isnumeric() and int(previous_result) != 0:        # Rest are execute iff last aprt has zero return value
                            execute = False
                    elif part.op == '&':
                        pass
                    elif part.op == ';':
                        execute = True
                        text = self.STDIO.read()
                        if len(text):
                            print(text)

                    else:
                        raise ValueError("Op type not implemented in interpreter")
        
        elif node.kind == 'compound':
            for part in node.list:
                vstr2 = NodeVisitor(part)
                self.interpreter(part, vstr2)
        
        elif node.kind == 'if':
            """ Structure of if node parts is [if, boolean, then, body, elif, boolean, then, body, else, body, fi] """
            parts = copy.copy(node.parts)
            while len(parts):
                # Nice stack based parsing stuff. Could formalize
                resv = parts.pop(0) # Remove if reserved word
                if resv.word != 'else': boolean_condition = parts.pop(0)
                if hasattr(parts[0], 'word') and parts[0].word =='then': parts.pop(0) # Remove then reserved word
                body = parts.pop(0)
                if parts[0].word == 'fi': parts.pop(0) # Remove the fi, if not loop
                
                # Determine truthiness
                boolean_string = str(NodeVisitor(boolean_condition)) 
                if boolean_string in self.truths:   # Check if user has already input the validity
                    resp = self.truths[boolean_string]
                else:                               # They haven't, so we need to ask
                    resp = ''
                    while resp != 't' and resp != 'f':
                        resp = input('Encountered Boolean condition ' + boolean_string + ' is it true or false? (t/f)')
                    self.truths[boolean_string] = resp

                if resp == 't': 
                    vstr2 = NodeVisitor(body)
                    self.interpreter(body, vstr2)
        
        elif node.kind == 'for':
            # This can be formalized in a real parser way. Need to find all forms of for loop though
            parts = node.parts
            if parts[0].word == 'for' and parts[2].word == 'in' and (parts[4].word == ';' or parts[4].word == 'do'):
                # Save the iterator to the variable list
                self.variables = bashparse.update_variable_list(node, self.variables)   
                var_name = node.parts[1].word
                var_values = copy.copy(self.variables[var_name])
                
                # Call the for loop
                parts = parts[5:]
                while hasattr(parts[0], 'word') and (parts[0].word == 'do' or parts[0].word == ';'):
                    parts.pop(0) 
                
                # Iterate over for loop values
                for val in var_values:
                    index = 0
                    self.variables[var_name] = [ var_values ]
                    # Call every function in for loop
                    for cmd in parts[:-1]: # last element is 'done'
                        vstr2 = NodeVisitor(cmd)
                        vstr2.apply(self.interpreter, vstr2)

                # Remove iterator from variable list cause scope
                self.variables.pop(var_name)
        else:
            print('node kind is: ', node.kind)
            print(node.dump())
            raise ValueError("Invalid Node type in interpreter")
        return bashparse.DONT_DESCEND


    def run(self, node):
        vstr = NodeVisitor(node)
        vstr.apply(self.interpreter, vstr)
        print(self.STDIO.read())


    def run_command(self, command, args):
        if command.kind == 'word':
            if command.word in self.bin:
                """ Very cheeky dynamic programming. Hopefully it doesn't kill performance too much """
                func = getattr(self, 'f_'+command.word)
                func(command, args)
            else: 
                resp = ''
                while resp != 'n' and resp != 'y':
                    resp = input('Unknown command ' + command.word + ' encouncered. Skip? (y/n)')
                if resp == 'n':
                    raise ValueError("Command " + command.word + " not implemented")
                elif resp == 'y':
                    pass

        elif command.kind == 'assignment':
            to_remove = []  # need to remove backwards to keep the indexes right
            
            """ Resolve the values from all command substitutions """
            for i, part in enumerate(command.parts):
                if part.kind == 'commandsubstitution':

                    # Create and execute command in subshell
                    subshell = Interpreter()
                    commandsub = part.command
                    subshell.run(commandsub)
                    results = subshell.STDIO.read()

                    # Adjust the tree with the replaced results
                    start = part.pos[0] - command.pos[0]
                    end = part.pos[0] - (command.pos[1] - command.pos[0])    # start + len
                    command.word = command.word[:start] + results + command.word[end:]
                    to_remove += [ i ]

            """ Removing the indexes backwards to keep the indexing correct """
            for index in reversed(to_remove):
                command.parts.pop(index)

            """ No command substitutions left.
                Replace and update the variable list. """
            replaced = bashparse.replace_variables(command, self.variables, replace_blanks=True)
            for node in replaced:
                self.variables = bashparse.update_variable_list(node, self.variables)

        else:
            print('command: ', command)
            raise ValueError('Command not implemented')


class Interpreter(InterpreterBase):
    
    def __init__(self, working_dir = '~'):
        super().__init__(working_dir)
    
    def f_echo(self, command, args):
        text = ''
        for node in args:
            text += node.word + ' '
        text = text[:len(text)-1]
        self.STDIO.write(text)

    def f_cd(self, command, args):
        if len(args) != 1: 
            print('bash: cd: too many arguments')
            self.STDIO.write('1')
        else: 
            self.working_dir = args[0].word
            self.STDIO.write('0')

    def f_wget(self, command, args):
        if validators.url(args[0].word): 
            filename = input('Wget requested "'+ args[0].word +'". Please enter a filename to pass in: ')
            file_contents = open(filename).read()
            self.fs[self.working_dir + '/' + 'index.html'] = File(name='index.html', contents=file_contents, permissions='rw-rw-rw-')
        else:
            raise ValueError("Invalid URL to wget")
    
    def f_chmod(self, command, args):
        if args[0].word == '+x':
            location = self.working_dir + '/' + args[1].word        # This actually doesn't work
            if location in self.fs: 
                permissions = self.fs[location].permissions
            else: 
                permissions = 'rw-rw-rw-'
                self.fs[location] = File(name=args[1].word, contents=None, permissions=permissions)
            perm_list = list(permissions)
            perm_list[2] = 'x'
            perm_list[5] = 'x'
            perm_list[8] = 'x'
            permissions = ''.join(perm_list)
            self.fs[location].setPermissions(permissions)
    
    def f_rm(self, command, args):
        if args[0].word in self.fs or self.working_dir+'/'+args[0].word in self.fs: self.fs.pop(args[0].word)
        else: print("rm: cannot remove '" + args[0].word + "': No such file or directory")
