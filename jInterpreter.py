#!/bin/python3
""" Bringing the death star to a knife fight """
import subprocess, os, stat, copy, json, re
import bashparse


""" Import the Parser and nodes that we created/need to deal with """
from jNode import Flag, Arg, Command
from jParser import Parser
from jRecord import Record
from bpFileSystem import FileSocket
from bpInterpreter import Interpreter as bpInterpreter


class InterpreterExitStatus:
    def __init__(self, message, status = 0, print_out=False):
        self.message = message
        self.print_out = print_out
        self.status = status
    
    def __str__(self):
        return 'ExitStatus{ ' + 'MESSAGE: ' + self.message + '; STATUS: ' + str(self.status) + '}'
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if self.message != other.message: return False
        if self.print_out != other.print_out: return False 
        if self.status != other.status: return False
        return True
    
    def print(self):
        if self.status:
            print("Judo Error")
        if self.status or self.print_out:
            print(self.message) 
        print('')     # Just add a space after every command is run. Nice for formatting



""" All the functional sections of the interpreter. 
    All node manipulation parts in InterpreterBase """
class Interpreter():
    def __init__(self, maintain_history = True):
        self.funcs = {
            'HELP': self.print_help,
            'LOAD': self.load,
            'NEXT': self.next, 
            'UNDO': self.undo,
            'SKIP': self.skip,
            'SAVE': self.save,
            'BUILD': self.build,
            'INCH': self.inch,
            'RUN': self.run,
            'STACK': self.stack,
            'DIR': self.dir,
            'STDIN': self.stdin,
            'STDOUT': self.stdout,
            'VAR': self.var,
            'FS': self.fs,
            'PARSE': self.parse,
            'HISTORY': self.history,
            'STATE': self.state, 
            'ALIAS': self.alias,
            'PASS': self.void,
            'VOID': self.void,
            'JSON':self.json,
            'EXIT': self.exit,
            'TOKENIZE':self.tokenize,
        }
        self.prog_nodes = None
        self.index = 0
        self.listening = True
        self.maintain_history = maintain_history
        self.parser = Parser('pass', {})
        self.env = bpInterpreter(STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {})
        self.history_stack = [ Record(env=self.env, name='init') ]

        self.reverse_aliases = {}

        for func_name in list(self.funcs.keys()):
            if func_name[0] not in self.funcs:
                self.reverse_aliases[func_name] = func_name[0]
                self.funcs[func_name[0]] = self.funcs[func_name]


    """ How to CLI is actually called in python """
    def listen(self):
        print('Welcome to the Judo shell')
        while self.listening:
            cmd = input(r'> ')                  # Get the text from the user
            prog = self.parser.parse(cmd)       # Parse the nodes and get the ast
            for cmd in prog.commands:           # Iterate over command nodes in the ast and execute them
                try:
                    func_name = cmd.func.upper()
                    if func_name not in self.funcs:
                        print(f"unknown command: {func_name}")
                        continue
                    func = self.funcs[cmd.func.upper()]     # Try to find the command in the cmd dict to execute
                except:                                     # Do nothing if its not found. Exiting the shell is annoying
                    print('Unknown Judo Command: ', cmd.func.upper())
                    print('Nothing was changed')
                    break
                exit_code = func(cmd.flags, *cmd.args)                  # Call the function if it was found

                exit_code.print()

    """ Converts arguments to strings. A necessary wrapper cause escape characters """
    def args_to_str(self, args, unescape=False):
        text = ''
        for arg in args:
            if unescape:
                text += arg.unescape() + ' '
            else:
                text += arg.value + ' '
        text = text[:-1]    # last space is wrong plz remove
        return text


    def print_help(self, flags, *args):
        output = "Commands:\n"

        for func_name in self.funcs:
            if func_name not in self.reverse_aliases.values():
                output += f"             {func_name}"
                if func_name in self.reverse_aliases:
                    output += f" ({self.reverse_aliases[func_name]})"
                elif self.funcs[func_name].__doc__:
                    docstr = self.funcs[func_name].__doc__
                    output += ": " + docstr[:docstr.find("\n")]

                output += "\n"

        return InterpreterExitStatus(message=output, print_out=True)


    def load(self, flags, *args):
        """ This loads a bash file into the prog_nodes attribute to be iterated through """
        filename = args[0].value
        self.prog_nodes = bashparse.parse(open(filename).read())
        self.index = 0
        return InterpreterExitStatus("SUCCESS")


    def next(self, flags, *args):
        """ Executes the next command in the node list. -e means the command should execute in surrounding env """
        def get_next_node():
            # if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
            if self.index > len(self.prog_nodes) - 1: return None
            node = self.prog_nodes[self.index]
            self.index = self.index + 1
            return node

        node = get_next_node()                         # Get the next node
        node_str = str(bashparse.NodeVisitor(node))

        """ All -e nodes need to be executed in environment so you can switch between them without issue """
        if self.maintain_history or Flag('h') in flags:
            self.save_state(action = node_str)

        if Flag('e') in flags:
            self.syscall(node_str)  # Convert to str then syscall

        if Flag('i') in flags:  # i flag means you want to inch it
            self.env.build(node, append = False)
        else:
            self.env.run(node)

        if Flag('p') in flags:
            return self.state([])

        return InterpreterExitStatus("SUCCESS")
        

    def undo(self, flags, *args):
        """ Undoes any action taken in the environment. Can't undo if it exited the env though """
        if len(self.history_stack) > 1:                     # Roll back if possible
            self.history_stack = self.history_stack[:-1]
            self.env = self.history_stack[-1].env
            self.index  = self.index - 1
        else:                                               # If not the re-create from the ground up
            self.env = bpInterpreter()
            self.history_stack = [ Record(env=self.env, name='init') ]
            self.index = 0
        return InterpreterExitStatus("SUCCESS")


    def skip(self, flags, *args):
        """ Move passed a node if the user doesn't care about it """
        self.index = self.index + 1
        return InterpreterExitStatus("SUCCESS")


    def save(self, flags, *args):
        """ Allows the user to create custom points in the history """
        if not len(args):
            return InterpreterExitStatus("Must specify a name for your save point. \nNothing was saved", status = 1)

        name = self.args_to_str(args)
        action = 'User Save'
        self.save_state(name=name, action=action)
        return InterpreterExitStatus("SUCCESS")


    def inch(self, flags, *args):
        """DOCS TBD  """
        res = self.env.inch()
        if not res:
            return InterpreterExitStatus("Action Stack is empty. Please run build or next/run -i to load the action stack", status = 1)
        return InterpreterExitStatus("SUCCESS")

    def run(self, flags, *args):
        """ Run a user input command by combining the args into a command and executing it. 
        All commands must also be run in env to maintain consistency. -i is a wrapper for build """
        text = self.args_to_str(args)

        if self.maintain_history or Flag('h') in flags:
            self.save_state(action = text)
        if Flag(value='e') in flags: 
            self.syscall(text)
        
        """ Adding -i is going to be a wrapper for build so it mirrors 'next' nicely """
        if Flag(value='i') in flags:
            self.build([], *args)
            return InterpreterExitStatus("SUCCESS")
        
        """ Even escaped commands must be run in env to maintain consistency when switching """
        nodes = bashparse.parse(text)
        for node in nodes:
            self.env.run(node)
        
        return InterpreterExitStatus("SUCCESS")


    """ Builds the action stack for a given command. Useful for debugging the bashparse interpreter """
    def build(self, flags, *args):
        # Convert args to command
        text = self.args_to_str(args)

        # Build the action stack for the node
        try:
            nodes = bashparse.parse(text)
            for node in nodes:
                self.env.build(node, append= Flag('a') in flags)
            return InterpreterExitStatus("SUCCESS")
        except:
            return InterpreterExitStatus(message="Bashparse cannot parse the code provided", status=1)


    def stack(self, flags, *args):
        """ Prints the action stack of the interpreter """
        message = 'Action Stack: ' + '\n'
        output_array = self.env.stack().split('\n')
        for el in output_array:
            message += '  ' + str(el) + '\n'
        return InterpreterExitStatus(message=message, print_out=True)


    def parse(self, flags, *args):
        """ Nice little parse wrapper """
        text = self.args_to_str(args)

        try:
            nodes = bashparse.parse(text)
            for node in nodes:
                print(node.dump())

            return InterpreterExitStatus("SUCCESS")

        except:
            return InterpreterExitStatus("Bashparse could not parse text", status = 1)


    def syscall(self, bashCommand):
        """ Writes the specified command into an executable file and runs it. 
        Then it prints the results """
        if type(bashCommand) is not str: return InterpreterExitStatus("Interpreter.syscall takes only a single text argument", status=1)
        """ Replace all the nodes using the environment """
        nodes = self.env.replace(bashparse.parse(bashCommand))
        
        """ Convert the replaced nodes to text """
        text = ' '.join( [ str(bashparse.NodeVisitor(x)) + '\n' for x in nodes ] )
        
        """ Execute the code """
        result = subprocess.run(text, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        """ Put results in the STDIO """
        output = str(result.stdout)
        if len(str(result.stderr)): output += '\n' + 'Error: ' + str(result.stderr)
        self.env.state.STDIO.OUT = output

        return InterpreterExitStatus("SUCCESS")


    def dir(self, flags, *args):
        """ Deals with the printing and modificaiton of the interpreters working directory """
        if len(args) == 1:
            self.env.working_dir(args[0].value)
            return InterpreterExitStatus(message = 'Working dir: ' + self.env.working_dir(), 
                        status=0, print_out=True)
        else : 
            return InterpreterExitStatus("Invalid number of arguments passed into DIR. Nothing changed", status=1)
        


    def stdin(self, flags, *args):
        """ For maintaining the STDIN for the current env """
        arg_text = self.args_to_str(args)
        if len(args):
            self.env.stdin(arg_text)
        return InterpreterExitStatus(message = "STD IN: " + self.env.stdin(), 
                    status=0, print_out=True)


    def stdout(self, flags, *args):
        """ For maintaining the STDOUT for the current env """
        arg_text = self.args_to_str(args)
        if len(args):
            self.env.stdout(arg_text)
        return InterpreterExitStatus(message="STD OUT: " + self.env.stdout(),
                    status=0, print_out=True)


    def var(self, flags, *args):
        """ For maintaining the variables in the current env """
        if len(args):
            """ Save the name:value combo from args until args is empty """
            while len(args) >= 3 and args[1] == Arg(':'):    # Man I hate this implementation
                self.env.set_variable(args[0].value, args[2].value) # Name:Value
                args = args[3:] if len(args) > 3 else []

        if Flag('p') in flags:
            return InterpreterExitStatus(message=self.env.text_variables(), print_out=True)

        return InterpreterExitStatus("SUCCESS")


    def fs(self, flags, *args):

        working_args = list(args)
        """ Strip out name:contents and name:contents:permissions, then save to env """
        while len(working_args):
            """ Strip the filename """
            file_name = working_args.pop(0).value

            """ Strip the : """
            if working_args[0] != Arg(':'): 
                return InterpreterExitStatus(status = 1, message = 'Invalid file formation. Please follow pattern: name:contents:permissions')
            working_args.pop(0)

            """ Get the file contents """
            if not len(working_args): return InterpreterExitStatus(status=1, message='Invalid file formation. File contents needed')
            file_contents = working_args.pop(0).value
            
            """ Get optional file permissions if next arg is : """
            if len(working_args) >= 2 and working_args[0] == Arg(':'):
                working_args.pop(0)     # remove :
                file_permissions = working_args.pop(0).value
            else:
                file_permissions = 'rw-rw-rw-'

            """ Update the file system """
            self.env.update_file_system(name=file_name, contents=file_contents, permissions=file_permissions)
        
        if Flag('p') in flags:
            return InterpreterExitStatus(message = self.env.text_filesystem(showFiles=True), print_out=True)

        return InterpreterExitStatus("SUCCESS")

    def state(self, flags, *args):
        """ Implementation of the state function. Prints if the -p flag is passed in """
        output = '\n' + self.env.stateText()
        return InterpreterExitStatus(message=output, print_out=True)


    def exit(self, flags, *args):
        """ Nicely exits the CLI """
        self.listening = False
        return InterpreterExitStatus("SUCCESS")
    

    def json(self, flags, *args):
        """ Imports / Exports the state to a JSON file """
        if len(args) != 1: 
            return InterpreterExitStatus("Wrong # of arguments. 1 filename must be specified", status = 1)

        filename = self.args_to_str(args)
        filename = filename if filename[-5:] == '.json' else filename + '.json'
        
        if Flag('i') in flags:  # Import
            data = json.load(open(filename))
            self.maintain_history = data['maintain_history'] == 't'
            self.history_stack = [ Record(**x) for x in data['history'] ]
            self.env = self.history_stack[-1].env
            for name, func in data['aliases'].items(): self.parser.lexer.add_alias(name, func)

        elif Flag('e') in flags: # Export
            history_array = [ x.json() for x in self.history_stack ]
            pre_json = { **{ "history":history_array }, **{"aliases":self.parser.json()},
                **{ "maintain_history": 't' if self.maintain_history else 'f' }
                 }
            
            fd = open(filename, "w")
            json.dump(pre_json, fd, indent=4)
        else:
            return InterpreterExitStatus('Please specify -i or -e', status = 2)

    def void(self, flags, *args):
        """ A simple function to not execute anything. Might be unnecessary but it exists """
        return InterpreterExitStatus("SUCCESS")


    def save_state(self, name = None, action = None):
        """ How the judo interpreter handles history. Creates a new bpInterpreter with a copy of the
        old state so it can be updated. Could move the history maintanace to the bpInterpreter instead """
        if name is None: name = str(len(self.history_stack))
        new_env = copy.deepcopy(self.env)
        self.history_stack += [ Record(env=new_env, name=name, action=action) ]
        self.env = new_env
        return InterpreterExitStatus("SUCCESS")
        
    

    def history(self, flags, *args):
        """ Implementation of the history command. Prints the history if -p is passed in.
        on/off/toggle will change if history is changed or not """
        to_return = InterpreterExitStatus("SUCCESS")
        if Flag('p') in flags or len(flags) == 0:
            output = '\n' + "History" + '\n'
            if len(self.history_stack):
                for record in self.history_stack: output += record.text(showFiles = False)
            else:
                output += "No History yet\n"
            to_return.message = output
            to_return.print_out = True
        if Arg('on') in args:
            self.maintain_history = True
        if Arg('off') in args:
            self.maintain_history = False
        if Arg('toggle') in args:
            self.maintain_history = not self.maintain_history
        return to_return
    

    def alias(self, flags, *args):
        """ How the interpreter handles the alias command. When its run, the command is passed to 
        the lexer so it will sub the command with the string passed in in the args. Last arg is the 
        name of the alias """
        to_return = InterpreterExitStatus("SUCCESS")
        if Flag('p') in flags:
            output = ''
            for el in args:
                output += el.value + ': ' + self.parser.lexer.json()[el.value] + '\n'
            to_return.message=output
            to_return.print_out=True

        else:
            alias = args[-1].value
            cmd_aliased = ' '.join( [ str(arg.value) for arg in args[:-1] ] ) # convert args to string
            self.parser.lexer.add_alias(alias, cmd_aliased)
        return to_return


    def tokenize(self, flags, *args):
        """ Exists for debugging, not listed in docs or test cause not suppoed to be public """
        new_lex = copy.copy(self.parser.lexer)
        new_lex.new(self.args_to_str(args))
        tokens = new_lex.get_all_tokens()
        output = ''
        for token in tokens:
            output += token.unescape()
        return InterpreterExitStatus(message=output, print_out=True)
