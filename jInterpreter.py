#!/bin/python3
""" Bringing the death star to a knife fight """
import subprocess, os, stat, copy, json
import bpInterpreter, bashparse


""" Import the Parser and nodes that we created/need to deal with """
from jNode import Flag, Arg, Command
from jParser import Parser
from jRecord import Record
from bpInterpreter import Interpreter as bpInterpreter


""" All the functional sections of the interpreter. 
    All node manipulation parts in InterpreterBase """
class Interpreter():
    def __init__(self, maintain_history = True):
        self.funcs = {
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
        }
        self.prog_nodes = None
        self.index = 0
        self.listening = True
        self.maintain_history = maintain_history
        self.parser = Parser('pass')
        self.env = bpInterpreter()
        self.history_stack = [ Record(env=self.env, name='init') ]


    """ How to CLI is actually called in python """
    def listen(self):
        print('Welcome to the Judo shell')
        while self.listening:
            cmd = input('> ')                   # Get the text from the user
            prog = self.parser.parse(cmd)       # Parse the nodes and get the ast
            for cmd in prog.commands:           # Iterate over command nodes in the ast and execute them
                try:
                    func = self.funcs[cmd.func.upper()]     # Try to find the command in the cmd dict to execute
                except:                                     # Do nothing if its not found. Exiting the shell is annoying
                    print('Unknown Judo Command: ', cmd.func.upper())
                    print('Nothing was changed')
                    break
                func(cmd.flags, *cmd.args)                  # Call the function if it was found


    """ Converts arguments to strings. A necessary wrapper cause escape characters """
    def args_to_str(self, args):
        text = ''
        for arg in args:
            text += arg.value + ' '
        text = text[:-1]    # last space is wrong plz remove
        text = text.replace('\\"', '"').replace('\\t', '    ')
        return text


    """ This loads a bash file into the prog_nodes attribute to be iterated through """
    def load(self, flags, *args):
        filename = args[0].value
        self.prog_nodes = bashparse.parse(open(filename).read())
        self.index = 0


    """ Executes the next command in the node list. -e means the command should execute in surrounding env """
    def next(self, flags, *args):
        def get_next_node():
            if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
            self.index = self.index + 1
            if self.index >= len(self.prog_nodes): return None
            node = self.prog_nodes[self.index]
            return node

        node = self.get_next_node()                         # Get the next node
        node_str = str(bashparse.NodeVisitor(node))
        if Flag('e') in flags: 
            self.syscall(node_str)  # Convert to str then syscall

        """ All -e nodes need to be executed in environment so you can switch between them without issue """
        if self.maintain_history or Flag('h') in flags:
            self.save_state(action = node_str)

        if Flag('i') in flags:  # i flag means you want to inch it
            self.env.build(node, append = False)
        else:
            self.env.run(node)

        """ Print the state cause its nice """
        self.state()


    """ Undoes any action taken in the environment. Can't undo if it exited the env though """
    def undo(self, flags, *args):
        if len(self.history_stack) > 1:                     # Roll back if possible
            self.env = self.history_stack[-1].env
            self.history_stack = self.history_stack[:-1]
            self.index  = self.index - 1
        else:                                               # If not the re-create from the ground up
            self.env = bpInterpreter.Interpreter()
            self.history_stack = [ Record(env=self.env, name='init') ]


    """ Move passed a node if the user doesn't care about it """
    def skip(self, flags, *args):
        self.index = self.index + 1


    """ Allows the user to create custom points in the history """
    def save(self, flags, *args):
        if not len(args):
            print("Must specify a name for your save point.")
            print("Nothing was saved")
            return 

        name = self.args_to_str(args)
        action = 'User Save'
        self.save_state(name=name, action=action)


    """  """
    def inch(self, flags, *args):
        res = self.env.inch()
        if not res:
            print("Action Stack is empty. Please run build or next/run -i to load the action stack")


    """ Run a user input command by combining the args into a command and executing it. 
        All commands must also be run in env to maintain consistency. -i is a wrapper for build """
    def run(self, flags, *args):
        text = self.args_to_str(args)

        if self.maintain_history or Flag('h') in flags:
            self.save_state(action = text)

        if Flag(value='e') in flags: 
            self.syscall(text)
        
        """ Adding -i is going to be a wrapper for build so it mirrors 'next' nicely """
        if Flag(value='i') in flags:
            self.build([], *args)
            return
        
        """ Even escaped commands must be run in env to maintain consistency when switching """
        nodes = bashparse.parse(text)
        for node in nodes:
            self.env.run(node)


    """ Builds the action stack for a given command. Useful for debugging the bashparse interpreter """
    def build(self, flags, *args):
        # Convert args to command
        text = self.args_to_str(args)

        # Build the action stack for the node
        nodes = bashparse.parse(text)
        for node in nodes:
            self.env.build(node, append= Flag('a') in flags)


    """ Prints the action stack of the interpreter """
    def stack(self, flags, *args):
        self.env.stack()


    """ Nice little parse wrapper """
    def parse(self, flags, *args):
        text = ''
        for arg in args:
            text += arg.value + ' '
        text = text[:-1]    # last space is wrong plz remove

        nodes = bashparse.parse(text)
        for node in nodes:
            print(node.dump())


    """ Writes the specified command into an executable file and runs it. 
        Then it prints the results """
    def syscall(self, bashCommand):
        """ Replace all the nodes using the environment """
        nodes = self.env.replace(bashparse.parse(bashCommand))
        
        """ Convert the replaced nodes to text """
        text = ' '.join( [ str(bashparse.NodeVisitor(x)) + '\n' for x in nodes ] )
        
        """ Execute the code """
        result = subprocess.run(text, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        """ Print results """
        print('Output: \n',  str(result.stdout))
        print('Error: \n', str(result.stderr))


    """ Deals with the printing and modificaiton of the interpreters working directory """
    def dir(self, flags, *args):
        if len(args) == 1:
            self.env.working_dir(args[0].value)
        else : print("Invalid number of arguments passed into DIR. Nothing changed")
        print('Working dir: ', self.env.working_dir())


    """ For maintaining the STDIN for the current env """
    def stdin(self, flags, *args):
        arg_text = self.args_to_str(args)
        if len(args):
            self.env.stdin(arg_text)
        print("STD IN: " + self.env.stdin())


    """ For maintaining the STDOUT for the current env """
    def stdout(self, flags, *args):
        arg_text = self.args_to_str(args)
        if len(args):
            self.env.stdout(arg_text)
        print("STD OUT: " + self.env.stdout())


    """ For maintaining the variables in the current env """
    def var(self, flags, *args):
        if len(args):
            """ Save the name:value combo from args until args is empty """
            while len(args) >= 3 and args[1] == Arg(':'):    # Man I hate this implementation
                self.env.set_variable(args[0].value, args[2].value) # Name:Value
                args = args[3:] if len(args) > 3 else []
        if Flag('p') in flags:
            self.env.print_variables()


    def fs(self, flags, *args):

        working_args = list(args)
        """ Strip out name:contents and name:contents:permissions, then save to env """
        while len(working_args):
            """ Strip the filename """
            file_name = working_args.pop(0).value

            """ Strip the : """
            if working_args.pop(0) != Arg(':'): 
                print('Invalid file formation. Please follow pattern: name:contents:permissions')
                return

            """ Get the file contents """
            if not len(working_args): print('Invalid file formation. File contents needed')
            file_contents = working_args.pop(0).value
            
            """ Get optional file permissions if next arg is : """
            if len(working_args) > 2 and working_args.pop(0) == Arg(':'):
                file_permissions = working_args.pop(0).value
            else:
                file_permissions = 'rw-rw-rw-'

            """ Update the file system """
            self.env.update_file_system(name=file_name, contents=file_contents, permissions=file_permissions)
        
        if Flag('p') in flags:
            self.env.print_filesystem(showFiles=True)


    """ Implementation of the state function. Prints if the -p flag is passed in """
    def state(self, flags, *args):
        print()
        self.env.showState()
        print()


    """ Nicely exits the CLI """
    def exit(self, flags, *args):
        self.listening = False
    

    """ Imports / Exports the state to a JSON file """
    def json(self, flags, *args):
        filename = self.args_to_str(args)
        filename = filename if filename[-5:] == '.json' else filename + '.json'
        
        if len(args) != 1: 
            print("Wrong # of arguments. 1 filename must be specified")
            return
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
            print('Please specify -i or -e')

    """ A simple function to not execute anything. Might be unnecessary but it exists """
    def void(self, flags, *args):
        pass


    """ How the judo interpreter handles history. Creates a new bpInterpreter with a copy of the
        old state so it can be updated. Could move the history maintanace to the bpInterpreter instead """
    def save_state(self, name = None, action = None):
        if name is None: name = str(len(self.history_stack))
        new_env = copy.deepcopy(self.env)
        self.history_stack += [ Record(env=new_env, name=name, action=action) ]
        self.env = new_env
        
    

    """ Implementation of the history command. Prints the history if -p is passed in.
        on/off/toggle will change if history is changed or not """
    def history(self, flags, *args):
        if Flag('p') in flags or len(flags) == 0:
            if len(self.history_stack):
                print('\n' + "History" + '\n')
                for record in self.history_stack: record.print(showFiles = False)
            else:
                print("No History yet")
        if Arg('on') in args:
            self.maintain_history = True
        if Arg('off') in args:
            self.maintain_history = False
        if Arg('toggle') in args:
            self.maintain_history = not self.maintain_history
    

    """ How the interpreter handles the alias command. When its run, the command is passed to 
        the lexer so it will sub the command with the string passed in in the args. Last arg is the 
        name of the alias """
    def alias(self, flags, *args):
        if Flag('p') in flags:
            for el in args:
                print(el.value, ': ', self.parser.lexer.json()[el.value])
            return
        alias = args[-1].value
        cmd_aliased = ' '.join( [ str(arg.value) for arg in args[:-1] ] ) # convert args to string
        self.parser.lexer.add_alias(alias, cmd_aliased)
