#!/bin/python3

import bashparse, copy, validators
from bashparse import NodeVisitor


def emptyFunc():
    pass


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
    
    def peek(self):
        return self.IN


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


class State:
    def __init__(self, STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {}):

        self.STDIO = STDIO
        self.working_dir = working_dir
        self.variables = variables
        self.fs = fs
        self.open_sockets = open_sockets
        self.truths = {}
    

    """ Print functionality for CLI (and I guess other purposes) """
    def show(self, showFiles = False):
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
    

    """ Update or create a file in the fs """
    def update_file_system(self, name,  contents, permissions, location = None):
        if location is None: location = self.working_dir
        self.fs[location + '/' + name] = File(name=name, contents=contents, permissions=permissions)
    

    """ Replace all the aliases possible in the state """
    def replace(self, nodes, replace_blanks = False):
        return bashparse.replace_variables(nodes, self.variables)
    


    """ Update the variables in the var list """
    def set_variable(self, name, value):
        if type(value) is not list: value = [ value ]
        self.variables[name] = value
    
    def update_variable_list(self, node):
        self.variables = bashparse.update_variable_list(node, self.variables)


class ActionEntry():

    def __init__(self, func, text):
        self.func = func
        self.text = text

    def __call__(self):
        self.func()
    
    def __str__(self):
        return self.text 

    def __repr__(self):
        return self.__str__()



class InterpreterBase():

    def __init__(self, STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {}):
        
        """ Where all the state info in help. Manipulated to allow for time travel """
        self.state = State(STDIO=STDIO, working_dir=working_dir, variables=variables, 
                            fs=fs, open_sockets=open_sockets, truths=truths)
        

        """ When traversing the AST we build an 'action queue' which holds all the actions 
            that need to be executed on the state in the order they should operate. 
            A normal bash lines calls the actions one after another but we build in the 
            capability to pause so we can do analysis. Actions need to read the state every time
            so that modifications can be made to state to prod actions of the script """
        self.action_queue = []


        """ Use introspection to add arbitrary functionality. Very cheeky """
        self.bin = []
        method_list = [ func for func in dir(Interpreter) if callable(getattr(Interpreter, func)) ]
        for method in method_list:
            if method[:2] == 'f_':
                self.bin += [ method[2:] ]


        self.execute = True


    """ Legacy wrappers. Will be removed eventually """
    def showState(self, showFiles = False):
        self.state.show(showFiles=showFiles)
        print('Action Queue Size: ', len(self.action_queue))

    def update_file_system(self, name,  contents, permissions, location = None):
        self.state.update_file_system(name, contents, permissions, location)

    def replace(self, nodes):
        return self.state.replace(nodes)
    
    def build(self, node, append = False):
        if not append: self.action_queue = []
        vstr = NodeVisitor(node)
        vstr.apply(self.interpreter, vstr)
        # print(self.state.STDIO.read())
    
    def stack(self):
        print('Action Stack: ')
        for el in self.action_queue:
            print('  ' + str(el))

    
    def set_variable(self, name, value):
        self.state.set_variable(name, value)


    """ The following section is everything necessary to actually run the interpreter """

    """ Run a single function off the action queue """
    def inch(self):
        func = self.action_queue.pop(0)
        func()
    

    """ Run everything off the action stack """
    def run(self, node = None):
        if node is not None: self.build(node)
        while len(self.action_queue): self.inch()

    """ This function builds the action queue and is effectively a switch statement 
        for each kind of node. Does not build any of the command functions. Calls 
        InterpreterBase.run_command() to do that """
    def interpreter(self, node, vstr):
        
        """ What to do when we encounter a pipeline node while traversing AST """
        if node.kind == 'pipeline':
            for i, part in enumerate(node.parts):
                if i % 2 != 0:
                    """ Action Queue Section """
                    action = ActionEntry(func=self.state.STDIO.transfer, text='pipeline transfer')
                    self.action_queue += [ action ] # Push the function onto the stack to be called later
                else:
                    """ Action Queue Section """
                    vstr2 = NodeVisitor(part)
                    self.interpreter(part, vstr2)
        

        elif node.kind == 'command':
            self.run_command(node.parts[0], node.parts[1:])


        elif node.kind == 'compound':
            for part in node.list:
                """ Action Queue Section """
                # Compound nodes don't need to be added to stack cause basically just wrapper ?
                action = ActionEntry(func=emptyFunc, text='compound node entry')
                self.action_queue += [ action ]
                vstr2 = NodeVisitor(part)
                self.interpreter(part, vstr2)


        elif node.kind == 'list':
            previous_result = None
            self.execute = True
            action = ActionEntry(func=emptyFunc, text='list node entry')
            self.action_queue += [ action ]

            for i, part in enumerate(node.parts):
                if i % 2 == 0:
                    # if self.execute:
                    vstr2 = NodeVisitor(part)
                    self.interpreter(part, vstr2)

                else:
                    def temp_func():
                        previous_result = self.state.STDIO.read()
                        if part.op == '||':
                            if previous_result.isnumeric() and int(previous_result) == 0:        # Rest are execute iff last aprt has non-zero return value
                                self.execute = False
                        elif part.op == '&&':  
                            if previous_result.isnumeric() and int(previous_result) != 0:        # Rest are execute iff last aprt has zero return value
                                self.execute = False
                        elif part.op == '&':
                            pass
                        elif part.op == ';':
                            self.execute = True
                            text = self.state.STDIO.read()
                            if len(text):
                                print(text)
                        else:
                            raise ValueError("Op type not implemented in interpreter")
                    action = ActionEntry(func=temp_func, text='list node transfer character: ' + part.op)
                    self.action_queue += [ action ]
        
        elif node.kind == 'for':
            # This can be formalized in a real parser way. Need to find all forms of for loop though
            parts = node.parts
            if parts[0].word == 'for' and parts[2].word == 'in' and (parts[4].word == ';' or parts[4].word == 'do'):
                """ Action Queue Section """
                # Save the iterator to the variable list as the initiation to the for loop
                # def temp_func():
                self.state.update_variable_list(node)
                action = ActionEntry(func=emptyFunc, text='for loop entry')
                self.action_queue += [ action ]
                
                var_name = node.parts[1].word
                var_values = copy.copy(self.state.variables[var_name])
            
                # Ignore unnecessary do and ; nodes
                parts = parts[5:]
                while hasattr(parts[0], 'word') and (parts[0].word == 'do' or parts[0].word == ';'):
                    parts.pop(0) 
                
                # Iterate over the values in the for loop
                for val in var_values:
                    # To initiate this iteration of the for loop
                    def temp_func():
                        self.state.set_variable(var_name, val)
                    action = ActionEntry(func=temp_func, text='Set loop iterator value for next itr')
                    self.action_queue += [ action ]
                    
                    # Push all the commands for this for loop iteration
                    for cmd in parts[:-1]: # last element is 'done'
                        # This should automatically append stuff to the action_stack so nothing really needs to be done?
                        vstr2 = NodeVisitor(cmd)
                        vstr2.apply(self.interpreter, vstr2)

                # Remove the iterator after the for loop exits
                # def temp_func():
                self.state.variables.pop(var_name)
                action = ActionEntry(func=emptyFunc, text='Exit for loop')
                self.action_queue += [ action ]


        elif node.kind == 'if':
             # Structure of if node parts is [if, boolean, then, body, elif, boolean, then, body, else, body, fi]
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
                    def temp_func():
                            vstr2 = NodeVisitor(body)
                            self.interpreter(body, vstr2)
                    action = ActionEntry(func=temp_func, text='If node with positive result')

        else:
            raise ValueError("Invalid Node type in bashparse interpreter: " + node.kind + '\n' + node.dump())

        return bashparse.DONT_DESCEND       # I feel like this is a bad way to use bashparse but too much thinking


    def run_command(self, command, args):
        if command.kind == 'word':
            if command.word in self.bin:
                """ Very cheeky dynamic programming. Hopefully it doesn't kill performance too much """
                func = getattr(self, 'f_'+command.word)
                # func(command, args)
                def temp_func():
                    func(command, args)
                action = ActionEntry(func=temp_func, text='Command node: ' + command.word)
                self.action_queue += [ action ]
            
            else: 
                def temp_func():
                    pass
                resp = ''
                while resp != 'n' and resp != 'y':
                    resp = input('Unknown command ' + command.word + ' encouncered. Skip? (y/n)')
                    print('resp value: ', resp)
                if resp == 'n':
                    raise ValueError("Command " + command.word + " not implemented")
                elif resp == 'y':
                    pass

                action = ActionEntry(func=temp_func, text='Unknown command: ' + command.word + '. Passing')
                
                self.action_queue += [ action ]


        elif command.kind == 'assignment':
            to_remove = []  # need to remove backwards to keep the indexes right
            
            """ Resolve the values from all command substitutions """
            for i, part in enumerate(command.parts):
                if part.kind == 'commandsubstitution':
                    def temp_func():
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
                    action = ActionEntry(func=temp_func, text='Resolving Command Substitution in Assignment')
                    self.action_queue += [ action ]

            """ Removing the indexes backwards to keep the indexing correct """
            for index in reversed(to_remove):
                command.parts.pop(index)

            """ No command substitutions left.
                Replace and update the variable list. """
            def temp_func():
                replaced = self.state.replace(command, replace_blanks=True)
                for node in replaced:
                    self.state.update_variable_list(node)
            action = ActionEntry(func=temp_func, text='Variable Assignment')
            self.action_queue += [ action ]

        else:
            print('command: ', command)
            raise ValueError('Command type not implemented: ' + str(command.kind))


class Interpreter(InterpreterBase):
    
    def __init__(self, STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {}):
        super().__init__(STDIO=STDIO, working_dir=working_dir, variables=variables, 
                            fs=fs, open_sockets=open_sockets, truths=truths)
    
    def f_echo(self, command, args):
        text = ''
        for node in args:
            text += node.word + ' '
        text = text[:len(text)-1]
        self.state.STDIO.write(text)

    def f_cd(self, command, args):
        if len(args) != 1: 
            print('bash: cd: too many arguments')
            self.state.STDIO.write('1')
        else: 
            self.working_dir = args[0].word
            self.state.STDIO.write('0')

    def f_wget(self, command, args):
        if validators.url(args[0].word): 
            filename = input('Wget requested "'+ args[0].word +'". Please enter a filename to pass in: ')
            file_contents = open(filename).read()
            self.update_file_system(name='index.html', contents=file_contents, permissions='rw-rw-rw-')
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
