from bpFileSystem import FileSocket
from bpPrimitives import ActionEntry, State
from bashparse import NodeVisitor
import copy, bashparse


class InterpreterBase():

    def __init__(self, STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {}, execute = True):

        """ Where all the state info in help. Manipulated to allow for time travel """
        self.state = State(STDIO=STDIO, working_dir=working_dir, variables=variables, 
                            fs=fs, open_sockets=open_sockets, truths=truths)


        """ When traversing the AST we build an 'action stack' which holds all the actions 
            that need to be executed on the state in the order they should operate. 
            A normal bash lines calls the actions one after another but we build in the 
            capability to pause so we can do analysis. Actions need to read the state every time
            so that modifications can be made to state to prod actions of the script """
        """ I'm aware this is a queue. Action Stack sounds better and the use of queue in the CLI
            might end up a little confusing """
        self.action_stack = []


        """ Use introspection to add arbitrary functionality. Very cheeky """
        self.bin = []
        method_list = [ func for func in dir(self) if callable(getattr(self, func)) ]
        for method in method_list:
            if method[:2] == 'f_':
                self.bin += [ method[2:] ]


        if type(execute) is str: execute = execute == 't'   # Used when loading from json
        self.execute = execute


    """ Used in Action Queues """
    def emptyFunc():
        pass


    """  """
    def json(self):
        return {**self.state.json(), **{ "execute": 't' if self.execute else 'f' }}
    

    """ Set the working directory """
    def working_dir(self, working_dir = None):
        if working_dir is not None: self.state.working_dir = str(working_dir)
        return self.state.working_dir


    """ Legacy wrappers. Will be removed eventually """
    def showState(self, showFiles = False):
        self.state.show(showFiles=showFiles)
        print('Action Queue Size: ', len(self.action_stack))

    def update_file_system(self, name,  contents, permissions, location = None):
        self.state.update_file_system(name, contents, permissions, location)

    def replace(self, nodes):
        return self.state.replace(nodes)
    
    def build(self, node, append = False):
        if not append: self.action_stack = []
        vstr = NodeVisitor(node)
        vstr.apply(self.interpreter, vstr)
    
    def stack(self):
        print('Action Stack: ')
        for el in self.action_stack:
            print('  ' + str(el))
        if not len(self.action_stack):
            print('Empty')
        

    
    def set_variable(self, name, value):
        self.state.set_variable(name, value)

    def print_variables(self):
        self.state.showVariables()
    
    def print_filesystem(self):
        self.state.showFileSystem()
    
    def stdin(self, IN = None):
        if IN is not None: self.state.STDIO.IN = IN
        return self.state.STDIO.IN

    def stdout(self, IN = None):
        if IN is not None: self.state.STDIO.OUT = IN
        return self.state.STDIO.OUT

    """ The following section is everything necessary to actually run the interpreter """

    """ Run a single function off the action stack """
    def inch(self):
        if len(self.action_stack):
            func = self.action_stack.pop(0)
            func()
            return True
        else:
            return False
    

    """ Run everything off the action stack """
    def run(self, node = None):
        if node is not None: self.build(node)
        while len(self.action_stack): self.inch()

    """ This function builds the action stack and is effectively a switch statement 
        for each kind of node. Does not build any of the command functions. Calls 
        InterpreterBase.run_command() to do that """
    def interpreter(self, node, vstr):
        
        """ What to do when we encounter a pipeline node while traversing AST """
        if node.kind == 'pipeline':
            for i, part in enumerate(node.parts):
                if i % 2 != 0:
                    """ Action Queue Section """
                    action = ActionEntry(func=self.state.STDIO.transfer, text='pipeline transfer')
                    self.action_stack += [ action ] # Push the function onto the stack to be called later
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
                action = ActionEntry(func=self.emptyFunc, text='compound node entry')
                self.action_stack += [ action ]
                vstr2 = NodeVisitor(part)
                self.interpreter(part, vstr2)


        elif node.kind == 'list':
            previous_result = None
            self.execute = True
            action = ActionEntry(func=self.emptyFunc, text='list node entry')
            self.action_stack += [ action ]

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
                    self.action_stack += [ action ]
        
        elif node.kind == 'for':
            # This can be formalized in a real parser way. Need to find all forms of for loop though
            parts = node.parts
            if parts[0].word == 'for' and parts[2].word == 'in' and (parts[4].word == ';' or parts[4].word == 'do'):
                """ Action Queue Section """
                # Save the iterator to the variable list as the initiation to the for loop
                # def temp_func():
                self.state.update_variable_list(node)
                action = ActionEntry(func=self.emptyFunc, text='for loop entry')
                self.action_stack += [ action ]
                
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
                    self.action_stack += [ action ]
                    
                    # Push all the commands for this for loop iteration
                    for cmd in parts[:-1]: # last element is 'done'
                        # This should automatically append stuff to the action_stack so nothing really needs to be done?
                        vstr2 = NodeVisitor(cmd)
                        vstr2.apply(self.interpreter, vstr2)

                # Remove the iterator after the for loop exits
                # def temp_func():
                self.state.variables.pop(var_name)
                action = ActionEntry(func=self.emptyFunc, textaction_queue='Exit for loop')
                self.action_stack += [ action ]


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
                self.action_stack += [ action ]
            
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
                
                self.action_stack += [ action ]


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
                    self.action_stack += [ action ]

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
            self.action_stack += [ action ]

        else:
            print('command: ', command)
            raise ValueError('Command type not implemented: ' + str(command.kind))
