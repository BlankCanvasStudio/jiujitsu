from jiujitsu.bpFileSystem import FileSocket
from jiujitsu.bpPrimitives import ActionEntry, State

from bashparser import NodeVisitor

import copy, bashparser, subprocess


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
    def transferFunc(self):
        # self.stdout('')
        self.state.print_to_screen()
    
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


    """ Used to manage the screen aspect of the state """
    def get_screen(self):
        return self.state.get_screen()

    def clear_screen(self):
        self.state.clear_screen()
        

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

    def enter_subshell(self):
        self.state.enter_subshell()


    def update_file_system(self, name,  contents, permissions='rw-rw-rw-', location = None):
        if type(name) is not str: raise InterpreterError('Interpreter.update_file_system(name != str)')
        if type(contents) is not str: raise InterpreterError('Interpreter.update_file_system(contents != str)')
        if type(permissions) is not str: raise InterpreterError('Interpreter.update_file_system(permissions != str)')
        if location and type(location) is not str: raise InterpreterError('Interpreter.update_file_system(location != str)')
        self.state.update_file_system(name, contents, permissions, location)


    def replace(self, nodes, full = False):
        if type(nodes) is not list: nodes = [ nodes ]
        for node in nodes:
            if type(node) is not bashparser.node: raise InterpreterError('Interpreter.replace() takes an array of bashparser nodes as its argument')
        return self.state.replace(nodes, full=full)


    def initialize_state_for_new_command(self):
        self.state.STDOUT('')
        self.state.STDIN('')

    def exit_node_cleanup(self):
        if len(self.state.STDOUT()):
            self.state.print_to_screen()
        self.state.STDIN('')


    def build(self, node, append = False):
        if type(node) is not bashparser.node: raise InterpreterError('Interpreter.build(node != bashparser.node)')
        if type(append) is not bool: raise InterpreterError('Interpreter.build(append != bashparser.node)')
        if not append: self.action_stack = []
       
        """
        # Remove the quote offsets from the AST because its annoying
        def quote_removal(node, vstr):
            if node.kind == 'assignment' or node.kind == 'word':
                if len(node.word) != node.pos[1] - node.pos[0]: # Then its quoted
                    bashparser.ast.shift_ast_right_of_path(vstr.root, vstr.path, 2) # Remove the delta for both the quotes
                    node.pos = ( node.pos[0], node.pos[0] + len(node.word))
        """
        action = ActionEntry(func=self.initialize_state_for_new_command, text='Initialize state for command')
        self.action_stack += [ action ]

        vstr = NodeVisitor(node)
        # vstr.apply(quote_removal, vstr)
        vstr.apply(self.interpreter, vstr)

        action = ActionEntry(func=self.exit_node_cleanup, text='Exit Node Cleanup')
        self.action_stack += [ action ]


    def stack(self):
        output = ''
        for el in self.action_stack:
            output += str(el) + '\n'
        if not len(self.action_stack):
            output += 'Empty' + '\n'
        return output


    def shell(self, text, forward_stdio = True):
        repl_nodes = self.replace(bashparser.parse(text), full = True)
        
        for node in repl_nodes:
            repl_text = str(bashparser.NodeVisitor(node))
            if forward_stdio:
                repl_text = 'echo "' + self.stdin() + '" | ' + repl_text
            
            """ Execute the code """
            result = subprocess.run(repl_text, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            """ Put results in the STDIO """
            output = result.stdout
            if len(str(result.stderr)): output += result.stderr
            self.state.STDOUT(output)

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

    def shift_variables(self):
        self.state.shift_variables()

    def set_truth(self, name, value):
        if type(name) is not str: raise InterpreterError('Interpreter.set_truth(name != str)')
        if type(value) is not bool and type(value) is not str: 
            raise InterpreterError('Interpreter.set_truth(value != str and value != bool)')
        if type(value) is not bool: 
            truths = ['t', 'true']
            value = value.lower() in truths
        self.state.set_truth(name, value)


    def get_truth(self, name):
        return self.state.test_truth(name)

    def test_truth(self, name):
        return self.state.test_truth(name)


    def query_user_for_truth(self, name):
        if type(name) is not str: raise InterpreterError('Interpreter.set_truth(name != str)')
        value = self.state.test_truth(name)
        if value is None:
            # Prompt and get the truth of statement
            print('Truth '+ name + ' not saved in state.')
            resp = input('Is it true, false, or would you like to execute it in the outside env? (t/f/e) ')
            while resp != 't' and resp != 'f' and resp != 'e':
                resp = input('Enter t or f')
            
            if resp == 'e': return resp
            
            value = resp == 't'

            # Save the value if they'd like
            print('Would you like to add this evaluation to the state for future use?')
            while resp != 'n' and resp != 'y':
                resp = input('(y/n) ')
            if resp == 'n':
                pass
            elif resp == 'y':
                self.set_truth(name, resp == 't')

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
            # load stdin if there are redirects
            if hasattr(node, 'redirects') and len(node.redirects):
                def tmp_func():
                    self.state.screens_above += [ self.state.screen ]
                    self.state.screen = ""
                action = ActionEntry(text="Prepare compound node for redirects", func=tmp_func)
                self.action_stack += [ action ]

                for part in reversed(node.redirects):
                    if (part.type == '<'): # ie we are loading in the redirect in some way
                        def tmp_func(part):
                            filename = str(NodeVisitor(part.output))
                            if filename in self.state.fs:
                                self.state.STDIN(self.state.fs[filename].contents)
                            else:
                                filename = input('Redirect node is asking for file <'+filename+'> Please enter a file you wish to upload: ')
                                file_contents = open(filename).read()
                                self.state.STDIN(file_contents)
                        action = ActionEntry(text='Get information from redirects', func=tmp_func, args=[part])
                        self.action_stack += [ action ]
                        break

            for part in node.list:
                """ Action Queue Section """
                # Compound nodes don't need to be added to stack cause basically just wrapper ?
                # action = ActionEntry(func=self.transferFunc, text='compound node entry')
                # self.action_stack += [ action ]
                vstr2 = NodeVisitor(part)
                self.interpreter(part, vstr2)
            
            # Save output if there are any redirects
            if hasattr(node, 'redirects') and len(node.redirects):
                for part in reversed(node.redirects):
                    # ALSO NEED CASES FOR 1> AND 2> ALSO >&
                    if (part.type == '>'): # ie we are loading in the redirect in some way
                        def tmp_func(part):
                            filename = str(NodeVisitor(part.output))
                            output = self.state.get_screen() + self.state.STDOUT()
                            self.state.update_file_system(filename, output)
                        action = ActionEntry(text='Move information out to redirects', func=tmp_func, args=[part])
                        self.action_stack += [ action ]
                        break
                def tmp_func():
                    self.state.screen = self.state.screens_above[-1]
                    self.state.screens_above = self.state.screens_above[:-1]

                action = ActionEntry(text="Exit compound node redirects", func=tmp_func)
                self.action_stack += [ action ]



        elif node.kind == 'list':
            self.execute = True
            action = ActionEntry(func=self.transferFunc, text='list node entry')
            self.action_stack += [ action ]

            for i, part in enumerate(node.parts):
                if i % 2 == 0:              # Its an actual command
                    action = ActionEntry(text='Resetting for new command', func=self.transferFunc)
                    self.action_stack += [ action ]
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
            action = ActionEntry(func=self.transferFunc, text='for loop entry')
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
                
                def itr_for_loop():
                    self.state.print_to_screen()

                action = ActionEntry(func=itr_for_loop, text='iterate for loop')
                self.action_stack += [ action ]

            # Remove the iterator after the for loop exits
            self.state.variables.pop(var_name)

            action = ActionEntry(func=self.transferFunc, text='Exit for loop')
            self.action_stack += [ action ]


        elif node.kind == 'if':
             # Structure of if node parts is [if, boolean, then, body, elif, boolean, then, body, else, body, fi]
            parts = copy.copy(node.parts)
            all_boolean_conditions = [] # Used to check if 'else' section needs to exe
            while len(parts):
                # Nice stack based parsing stuff. Could formalize. Lmao, I did
                resv = parts.pop(0) # Remove if/elif/else reserved word
                boolean_string = ''
                if resv.word != 'else': 
                    boolean_condition = parts.pop(0)
                    boolean_string = str(NodeVisitor(boolean_condition))
                    parts.pop(0)    # Remove then reserved word

                body = []
                while len(parts) and parts[0].kind !='reservedword': body += [ parts.pop(0) ]
                if parts[0].word == 'fi': parts.pop(0) # Remove the fi, if not loop


                def find_truth(boolean_string):
                    # Determine truthiness
                    if boolean_string in self.state.truths:   # Check if user has already input the validity
                        resp = self.state.truths[boolean_string]
                    else:                               # They haven't, so we need to asklini
                        resp = self.query_user_for_truth(boolean_string)
                        
                        if resp != 'e':
                            self.state.truths[boolean_string] = resp
                            return
                        
                        # Set up the execution option
                        old_action_stack = copy.deepcopy(self.action_stack)
                        self.action_stack = []
                        # Remove ; to present the resetting of the output
                        boolean_string_trimmed = boolean_string
                        if boolean_string[-1] == ';': 
                            boolean_string_trimmed = boolean_string[:-1]
                        self.interpreter(bashparser.parse(boolean_string_trimmed)[0], self)
 

                        def check_if_boolean_passed(boolean_string):
                            if self.state.STDOUT() == '': self.state.truths[boolean_string] = 'f'
                            else : self.state.truths[boolean_string] = 't'
                            self.state.STDOUT('')

                        self.action_stack += [ ActionEntry(func=check_if_boolean_passed, args=[boolean_string], text='Determine if boolean execution is true') ]
                        self.action_stack += old_action_stack

                def execte_truth(boolean_string, body, all_boolean_conditions, if_type):
                    # If one before executed, skip out 
                    for condition in all_boolean_conditions: 
                        if self.state.truths[condition] == 't': return

                    if if_type=='else' or self.state.truths[boolean_string] == 't': 
                        if type(body) is not list: body = [ body ]
                        # Save the current action stack, generate a new body, append the action stack to it
                        # This way we can inject commands into the action stack during run time. It sucks but necessary
                        old_action_stack = copy.deepcopy(self.action_stack)
                        enter_loop = ActionEntry(text = 'Enter If Statement Execution Block', func=self.transferFunc)
                        add_to_action_stack = [ enter_loop ]
                        for node in body:
                            self.action_stack = []
                            vstr2 = NodeVisitor(node)
                            self.interpreter(node, vstr2)
                            add_to_action_stack += self.action_stack
                        
                        def exit_if_statement():
                            self.state.print_to_screen()
                        exit_loop = ActionEntry(text='Exit If Statement Execution Block', func=exit_if_statement)
                        add_to_action_stack += [ exit_loop ]
                        self.action_stack = add_to_action_stack + old_action_stack
                
                def else_function():
                    pass    
                
                if resv.word == 'else':
                    truth_action = ActionEntry(func = else_function, text='Determine if else should execute')
                else:
                    truth_action = ActionEntry(func = find_truth, args=[boolean_string], text='Determine boolean statement truth')

                build_results = ActionEntry(func = execte_truth, args=[boolean_string, body, copy.copy(all_boolean_conditions), resv.word], text='Possibly append actions to stack')   

                if len(boolean_string):
                    all_boolean_conditions += [ boolean_string ]

                self.action_stack += [ truth_action, build_results ]
        
        elif node.kind == 'reservedword':
            if node.word == '(':
                def temp_func():
                    self.state.lower_scope()
                self.action_stack += [ ActionEntry(func=temp_func, text="Entering sub-shell env") ]
            elif node.word == ')':
                def temp_func():
                    self.state.print_to_screen()
                    self.state.raise_scope()
                self.action_stack += [ ActionEntry(func=temp_func, text="Exiting sub-shell env") ]

            else:
                raise ValueError("Invalid Resevered Word Node type in bashparser interpreter: " + node.kind + '\n' + node.dump())

        elif node.kind == 'function': 
            self.state.build_functions(node)

        else:
            raise ValueError("Invalid Node type in bashparser interpreter: " + node.kind + '\n' + node.dump())


        return bashparser.DONT_DESCEND       # I feel like this is a bad way to use bashparser but too much thinking


    def resolve_command_substitution(self, node):
        if not hasattr(node, 'parts'): return 
        for i, part in enumerate(reversed(node.parts)):
            if part.kind == 'commandsubstitution':
                
                def build_cmd_sub(node, part):
                    # Enter the subshell
                    self.state.lower_scope()

                    # Build the new commands 
                    commandsub = part.command
                    old_action_stack = copy.copy(self.action_stack)
                    self.action_stack = []
                    self.interpreter(commandsub, self)
                    self.action_stack += old_action_stack
 
                def replace_cmd_sub_results(node, part, index):
                    screen_string = ' '.join(self.state.get_screen().split('\n'))
                    results = screen_string + ' ' + self.stdout() if len(screen_string) else self.stdout()
                    if self.stdout() == '' and len(screen_string): results = results[:-1] # remove bad trailing space
                    self.stdout('')
                    self.state.screen = "" # empty screen so it doesn't get appended to
                    
                    # Adjust the tree with the replaced results
                    index_one = part.pos[0] - node.pos[0]
                    orig_index_one = index_one  # sloppy coding but it works so whatever

                    # If the string is quoted in any way the $ will be offset from the actual pos
                    # This is how we identify if we need to verify pos and find new pos
                    starting_offset = -1
                    while node.word[index_one] != '$':
                        index_one = orig_index_one + starting_offset
                        starting_offset = abs(starting_offset) if starting_offset < 0 else -(starting_offset + 1)
 


                    node.word = node.word[:index_one] + results + node.word[index_one + (part.pos[1] - node.pos[0]):]
                    node.parts = node.parts[:index] + node.parts[index + 1:]
                    # Exit the subshell env
                    self.state.raise_scope()

                action = ActionEntry(func=build_cmd_sub, args=[node,part], text='Enter Command Substitution Env: ' + str(bashparser.NodeVisitor(node)), code=str(bashparser.NodeVisitor(node)))
                self.action_stack += [ action ]
                action = ActionEntry(func=replace_cmd_sub_results, args=[node, part, len(node.parts) - 1 - i], text='Exiting Command Substitution Env: ' + str(bashparser.NodeVisitor(node)), code=str(bashparser.NodeVisitor(node)))
                self.action_stack += [ action ]

    def run_command(self, command, args, node):

        if command.kind == 'word':
            for part in node.parts:
                self.resolve_command_substitution(part)
            def temp_func(command, args, node):
                command = node.parts[0]
                # Add section to do function resoution here
                if command.word in self.state.functions:
                    # Let the user know whats happening
                    resolved_node = self.state.resolve_functions(copy.deepcopy(node))
                    
                    function_arguments = {}
                    for argument in args:
                        argument = self.replace(argument, full=False)[0]
                        function_arguments[str(len(function_arguments) + 1)] = argument.word

                    old_action_stack = copy.deepcopy(self.action_stack)
                    self.action_stack = []

                    # Enter the function scope
                    def lower_scope(function_args):
                        self.state.lower_scope()
                        for key, value in function_args.items():
                            self.state.set_variable(key, value)
                    
                    action = ActionEntry(func=lower_scope, args=[function_arguments], text='Enter the function scope')
                    self.action_stack = [ action ] + self.action_stack
                    
                    # Build new action stack for the body of the function
                    self.interpreter(resolved_node, self)

                    # Leave the function scope
                    def exit_function_scope():
                        if self.state.STDOUT():
                            self.state.print_to_screen()
                        self.state.raise_scope()
                    # action = ActionEntry(func=self.state.raise_scope, text='Exit the function scope')
                    action = ActionEntry(func=exit_function_scope, text='Exit the function scope')

                    self.action_stack = self.action_stack + [ action ]

                    self.action_stack += old_action_stack


                elif command.word in self.bin:
                    """ Very cheeky dynamic programming. Hopefully it doesn't kill performance too much """
                    func = getattr(self, 'f_'+command.word)
                    node = self.replace(node)[0]
                    func(node)

                else: 
                    if len(command.word.strip()) or len(args):
                        resp = ''
                        while resp != 's' and resp != 'e':
                            resp = input('Unknown command ' + command.word + ' encouncered. Skip or execute in outside env? (s/e) ')
                        if resp == 's':
                            pass
                        elif resp == 'e':
                            self.shell(str(NodeVisitor(node)))

            action = ActionEntry(func=temp_func, text='Command node: ' + command.word, args=[command, args, node], code=str(bashparser.NodeVisitor(node)))
            self.action_stack += [ action ]



        elif command.kind == 'assignment':
            action = ActionEntry(func=self.transferFunc, text='Entering Assignment Node: ' + str(NodeVisitor(command)))
            self.action_stack += [ action ]
            for part in node.parts:
                if len(part.parts):
                    self.resolve_command_substitution(part)

            """ No command substitutions left.
                Replace and update the variable list. """
            def temp_func(command):
                replaced = self.state.replace(command, replace_blanks=True, full=False)
                for node in replaced:
                    self.state.update_variable_list(node)
            action = ActionEntry(func=temp_func, args=[command], text='Variable Assignment', code=str(bashparser.NodeVisitor(node)))
            self.action_stack += [ action ]

        else:
            print('command: ', command)
            raise ValueError('Command type not implemented: ' + str(command.kind))

