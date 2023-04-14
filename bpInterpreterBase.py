from bpFileSystem import FileSocket
from bpPrimitives import ActionEntry, State
from bashparser import NodeVisitor
import copy, bashparser


class InterpreterError(Exception):
    pass


class InterpreterBase():

    def __init__(self, STDIO = None, working_dir = None, variables = None, 
                    fs = None, open_sockets = None, truths = None, execute = True):
        """ Irritating but necessary cause mutable arguments """
        if STDIO is None: STDIO = FileSocket(id_num = 0)
        if working_dir is None: working_dir = '~'
        if variables is None: variables = {}
        if fs is None: fs = {}
        if open_sockets is None: open_sockets = []
        if truths is None: truths = {}

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


    def __eq__(self, other):
        if len(self.action_stack) != len(other.action_stack): return False
        for i, el in enumerate(self.action_stack):
            if self.action_stack[i] != other.action_stack[i]: return False     
        if self.execute != other.execute: return False
        if self.state != other.state: return False
        return True


    """ Used in Action Queues """
    def emptyFunc(self):
        pass


    """ Used when converting CLI state to json file """
    def json(self):
        return {**self.state.json(), **{ "execute": 't' if self.execute else 'f' }}
    
    """ Used to convert a node into a command and argument. Need for by reference substitution in CMD SUBS and 
        has to be used in any interpreter functions implemented """
    def parse_node(self, node):
        cmd = node.parts[0]
        args = node.parts[1:]
        return cmd, args


    """ Set the working directory """
    def working_dir(self, working_dir = None):
        if working_dir is not None: self.state.working_dir = str(working_dir)
        return self.state.working_dir


    """ The following 2 functions need to be this similar to make the CLI and 
        python implementations work """
    def showState(self, showFiles = False):
        if type(showFiles) is not bool: raise InterpreterError('Error. Interpreter.showState(showFiles != bool)')
        print(self.stateText(showFiles=showFiles))
    
    def stateText(self, showFiles = False):
        if type(showFiles) is not bool: raise InterpreterError('Error. Interpreter.showText(showFiles != bool)')
        output = self.state.text(showFiles=showFiles) + '\n'
        output += 'Action Queue Size: ' + str(len(self.action_stack))
        return output


    def update_file_system(self, name,  contents, permissions='rw-rw-rw-', location = None):
        if type(name) is not str: raise InterpreterError('Interpreter.update_file_system(name != str)')
        if type(contents) is not str: raise InterpreterError('Interpreter.update_file_system(contents != str)')
        if type(permissions) is not str: raise InterpreterError('Interpreter.update_file_system(permissions != str)')
        if location and type(location) is not str: raise InterpreterError('Interpreter.update_file_system(location != str)')
        self.state.update_file_system(name, contents, permissions, location)


    def replace(self, nodes):
        if type(nodes) is not list: nodes = [ nodes ]
        for node in nodes:
            if type(node) is not bashparser.node: raise InterpreterError('Interpreter.replace() takes an array of bashparser nodes as its argument')
        return self.state.replace(nodes)


    def initialize_state_for_new_command(self):
        self.state.STDOUT('')
        self.state.STDIN('')


    def build(self, node, append = False):
        if type(node) is not bashparser.node: raise InterpreterError('Interpreter.build(node != bashparser.node)')
        if type(append) is not bool: raise InterpreterError('Interpreter.build(append != bashparser.node)')
        if not append: self.action_stack = []

        action = ActionEntry(func=self.initialize_state_for_new_command, text='Initialize state for command')
        self.action_stack += [ action ]

        vstr = NodeVisitor(node)
        vstr.apply(self.interpreter, vstr)


    def stack(self):
        output = ''
        for el in self.action_stack:
            output += str(el) + '\n'
        if not len(self.action_stack):
            output += 'Empty' + '\n'
        return output


    def set_variable(self, name, value):
        if type(name) is not str: raise InterpreterError('Interpreter.set_variable(name != str)')
        if type(value) is not list: value = [ value ]
        for el in value: 
            if type(el) is not str: raise InterpreterError('Interpreter.set_variable(value != str or list of str)')
        self.state.set_variable(name, value)


    def print_variables(self):
        print(self.text_variables())


    def text_variables(self):
        return self.state.variablesText()


    def set_truth(self, name, value):
        if type(name) is not str: raise InterpreterError('Interpreter.set_truth(name != str)')
        if type(value) is not bool and type(value) is not str: 
            raise InterpreterError('Interpreter.set_truth(value != str and value != bool)')
        if type(value) is not bool: 
            truths = ['t', 'true']
            value = value.lower() in truths
        self.state.set_truth(name, value)


    def test_truth(self, name):
        if type(name) is not str: raise InterpreterError('Interpreter.set_truth(name != str)')
        value = self.state.test_truth(name)
        if value is None:
            print('Truth '+ name + ' not in truth dictionary. Add it?')
            resp = ''
            while resp != 'n' and resp != 'y':
                resp = input('(y/n)')
            if resp == 'n':
                raise InterpreterError('InterpreterBase.test_truth is unknown and user refused to add.')
            elif resp == 'y':
                while resp != 't' and resp != 'f':
                    resp = input('Enter t or f')
                self.set_truth(name, resp == 't')
                value = resp == 't'
        return value


    def print_filesystem(self, showFiles = False):
        print(self.text_filesystem(showFiles=showFiles))


    def text_filesystem(self, showFiles = False):
        return self.state.fileSystemText(showFiles=showFiles)


    def stdin(self, IN = None):
        if IN and type(IN) is not str: raise InterpreterError('Error Interpreter.stdin(IN != str)')
        if IN is not None: self.state.STDIN(IN)
        return self.state.STDIN()


    def stdout(self, OUT = None):
        if OUT and type(OUT) is not str: raise InterpreterError('Error Interpreter.stdout(OUT != str)')
        if OUT is not None: self.state.STDOUT(OUT)
        return self.state.STDOUT()


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
        if node and type(node) is not bashparser.node: raise InterpreterError('Error. Interpreter.run(node != bashparser.node)')
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
            self.run_command(node.parts[0], node.parts[1:], node)


        elif node.kind == 'compound':
            for part in node.list:
                """ Action Queue Section """
                # Compound nodes don't need to be added to stack cause basically just wrapper ?
                action = ActionEntry(func=self.emptyFunc, text='compound node entry')
                self.action_stack += [ action ]
                vstr2 = NodeVisitor(part)
                self.interpreter(part, vstr2)


        elif node.kind == 'list':
            self.execute = True
            action = ActionEntry(func=self.emptyFunc, text='list node entry')
            self.action_stack += [ action ]

            for i, part in enumerate(node.parts):
                if i % 2 == 0:              # Its an actual command
                    vstr2 = NodeVisitor(part)
                    self.interpreter(part, vstr2)

                else:                       # Its a pipeline or something to that end
                    def temp_func(part):
                        previous_result = self.state.STDIO.read()
                        if part.op == '||':
                            if previous_result.isnumeric() and int(previous_result) == 0:        # Rest are execute iff last aprt has non-zero return value
                                self.execute = False
                        elif part.op == '&&':  
                            if previous_result.isnumeric() and int(previous_result) != 0:        # Rest are execute iff last aprt has zero return value
                                self.execute = False
                        elif part.op == '&':
                            pass
                        elif part.op == ';' or part.op == '\n':
                            self.execute = True
                            self.state.STDIN('')
                            self.state.STDOUT('')
                        else:
                            raise ValueError("Op type not implemented in interpreter: ", part.op)

                    action = ActionEntry(func=temp_func, text='list node transfer character: ' + part.op.replace('\n', '\\n'), args=[part])
                    self.action_stack += [ action ]

        elif node.kind == 'for':
            # This can be formalized in a real parser way. Need to find all forms of for loop though
            parts = copy.copy(node.parts)

            """ Action Queue Section """
            # Save the iterator to the variable list 
            self.state.update_variable_list(node)
            action = ActionEntry(func=self.emptyFunc, text='for loop entry')
            self.action_stack += [ action ]

            var_name = node.parts[1].word
            var_values = self.state.variables[var_name]

            # Find the actual commands to execute by skipping header section
            while not (hasattr(parts[0], 'word') and parts[0].word == 'do'): parts.pop(0)
            parts.pop(0)       # Remove the actual 'do' node
            parts = parts[:-1] # Remove the done 

            # Iterate over the values in the for loop
            for val in var_values:
                # To initiate this iteration of the for loop
                def temp_func(var_name, val):
                    self.state.set_variable(var_name, val)
                action = ActionEntry(func=temp_func, args=[var_name, val], text='Set loop iterator value for next itr')
                self.action_stack += [ action ]

                # Push all the commands for this for loop iteration
                for cmd in parts: # last element is 'done'
                    # This should automatically append stuff to the action_stack so nothing really needs to be done?
                    vstr2 = NodeVisitor(cmd)
                    vstr2.apply(self.interpreter, vstr2)

            # Remove the iterator after the for loop exits
            self.state.variables.pop(var_name)
            action = ActionEntry(func=self.emptyFunc, text='Exit for loop')
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
                if boolean_string in self.state.truths:   # Check if user has already input the validity
                    resp = self.state.truths[boolean_string]
                else:                               # They haven't, so we need to ask
                    resp = ''
                    while resp != 't' and resp != 'f':
                        resp = input('Encountered Boolean condition ' + boolean_string + ' is it true or false? (t/f)')
                    self.state.truths[boolean_string] = resp
                if resp == 't': 
                    def temp_func():
                            vstr2 = NodeVisitor(body)
                            self.interpreter(body, vstr2)
                    action = ActionEntry(func=temp_func, text='If node with positive result')

        else:
            raise ValueError("Invalid Node type in bashparser interpreter: " + node.kind + '\n' + node.dump())

        return bashparser.DONT_DESCEND       # I feel like this is a bad way to use bashparser but too much thinking


    def resolve_command_substitution(self, node):
        for i, part in enumerate(node.parts):
            if part.kind == 'commandsubstitution':
                def temp_func(node, part):
                    Interpreter = self.__class__
                    subshell = Interpreter()
                    subshell.__init__()
                    commandsub = part.command
                    subshell.run(commandsub)
                    results = subshell.stdout()
                    subshell.stdout('')

                    # The file sytem in the subshell is going to update the current file system
                    self.state.fs.update(subshell.state.fs)

                    # Adjust the tree with the replaced results
                    node.word = node.word[:(part.pos[0] - node.pos[0])] + results + node.word[(part.pos[0] - node.pos[0]) + part.pos[1]:]

                action = ActionEntry(func=temp_func, args=[node, part], text='Resolving Command Substitution: ' + str(bashparser.NodeVisitor(node)), code=str(bashparser.NodeVisitor(node)))
                self.action_stack += [ action ]

    def run_command(self, command, args, node):

        if command.kind == 'word':
            for part in node.parts:
                self.resolve_command_substitution(part)
            def temp_func(command, args, node):
                command = node.parts[0]
                if command.word in self.bin:
                    """ Very cheeky dynamic programming. Hopefully it doesn't kill performance too much """
                    func = getattr(self, 'f_'+command.word)
                    # def temp_func(command, args, node):
                    node = self.replace(node)[0]
                    func(node)
                    # action = ActionEntry(func=temp_func, text='Command node: ' + command.word, args=[command, args, node], code=str(bashparser.NodeVisitor(node)))
                    # self.action_stack += [ action ]

                else: 
                    # def temp_func():
                    if len(command.word.strip()) or len(args):
                        resp = ''
                        while resp != 'n' and resp != 'y':
                            resp = input('Unknown command ' + command.word + ' encouncered. Skip? (y/n)')
                        if resp == 'n':
                            raise ValueError("Command " + command.word + " not implemented")
                        elif resp == 'y':
                            pass

                    # action = ActionEntry(func=temp_func, text='Unknown command: ' + command.word + '. Possibly Passing', code=str(bashparser.NodeVisitor(node)))

                    # self.action_stack += [ action ]

            action = ActionEntry(func=temp_func, text='Command node: ' + command.word, args=[command, args, node], code=str(bashparser.NodeVisitor(node)))
            self.action_stack += [ action ]



        elif command.kind == 'assignment':
            to_remove = []  # need to remove backwards to keep the indexes right
            for part in node.parts:
                if len(part.parts):
                    self.resolve_command_substitution(part)

            """ Removing the indexes backwards to keep the indexing correct """
            for index in reversed(to_remove):
                command.parts.pop(index)

            """ No command substitutions left.
                Replace and update the variable list. """
            def temp_func():
                replaced = self.state.replace(command, replace_blanks=True)
                for node in replaced:
                    self.state.update_variable_list(node)
            action = ActionEntry(func=temp_func, text='Variable Assignment', code=str(bashparser.NodeVisitor(node)))
            self.action_stack += [ action ]

        else:
            print('command: ', command)
            raise ValueError('Command type not implemented: ' + str(command.kind))