#!/bin/python3
""" Bringing the death star to a knife fight """
import subprocess, os, stat, copy
import bpInterpreter, bashparse


""" Import the Parser and nodes that we created/need to deal with """
from nodes import Flag, Arg, Command
from jParser import Parser
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
            'RUN': self.run,
            'BUILD': self.build,
            'STACK': self.stack,
            'PARSE': self.parse,
            'HISTORY': self.history,
            'STATE': self.state, 
            'ALIAS': self.alias,
            'PASS': self.void,
            'VOID': self.void,
            'EXIT': self.exit,
        }
        self.prog_nodes = None
        self.index = 0
        self.listening = True
        self.maintain_history = maintain_history
        self.parser = Parser('pass')
        self.env = bpInterpreter()
        self.history_stack = [ self.env ]


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


    """  """
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


    """ Executes the next command in the node list """
    def next(self, flags, *args):
        def get_next_node():
            if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
            self.index = self.index + 1
            if self.index >= len(self.prog_nodes): return None
            node = self.prog_nodes[self.index]
            return node

        node = self.get_next_node()                         # Get the next node
        if Flag('e') in flags: 
            self.syscall(str(bashparse.NodeVisitor(node)))  # Convert to str then syscall

        """ All -e nodes need to be executed in environment so you can switch between them without issue """
        if self.maintain_history or Flag('h') in flags:
            self.save_state()
        self.env.run(node)

        """ Print the state cause its nice """
        self.state()


    """ Undoes any action taken in the environment. Can't undo if it exited the env though """
    def undo(self, flags, *args):
        if len(self.history_stack) > 1:                     # Roll back if possible
            self.env = self.history_stack[-1]
            self.history_stack = self.history_stack[:-1]
            self.index  = self.index - 1
        else:                                               # If not the re-create from the ground up
            self.env = bpInterpreter.Interpreter()
            self.history_stack = [ self.env ]


    """ Move passed a node if the user doesn't care about it """
    def skip(self, flags, *args):
        self.index = self.index + 1


    """ Run a user input command by combining the args into a command and executing it. 
        All commands must also be run in env to maintain consistency """
    def run(self, flags, *args):
        if self.maintain_history or Flag('h') in flags:
            self.save_state()

        text = self.args_to_str(args)
        if Flag(value='e') in flags: 
            self.syscall(text)
        
        """ Even escaped commands must be run in env to maintain consistency when switching """
        nodes = bashparse.parse(text)
        for node in nodes:
            self.env.run(node)


    """ Builds the action stack for a given command. Useful for debugging the bashparse interpreter """
    def build(self, flags, *args):
        # Convert args to command
        text = self.args_to_str(args)

        print('build text: \n', text)

        append = Flag('a') in flags

        # Build the action stack for the node
        nodes = bashparse.parse(text)
        for node in nodes:
            self.env.build(node, append=append)


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


    """ Implementation of the state function. Prints if the -p flag is passed in """
    def state(self, flags, *args):
        """ Handle -s flag """
        if Flag('s') in flags:  # This means they want to set something in the file system
            if len(args) == 0:
                pass

            elif Arg('var') == args[0]: #  Save a variable 
                var_values = args[1:]   # Remove Arg{var}
                """ Save the name:value combo from var_values until var_values is empty """
                while len(var_values) >= 3 and var_values[1] == Arg(':'):    # Man I hate this implementation
                    self.env.set_variable(var_values[0].value, var_values[2].value) # Name:Value
                    var_values = var_values[3:] if len(var_values) > 3 else []
            
            elif Arg('fs') == args[0]:  # Save something to the file system
                working_args = args[1:]
                """ Strip out name:contents and name:contents:permissions, then save to env """
                while len(working_args):
                    """ Strip the filename """
                    file_name = working_args.pop(0).value
                    if working_args[0] != Arg(':'): 
                        print('Invalid file formation for state -s fs')
                        return
                   
                    """ Remove : """
                    working_args.pop(0)
                    
                    """ Get the file contents """
                    if not len(working_args): print('Invalid file formation for state -s fs. File contents needed')
                    file_contents = working_args.pop(0).value
                    
                    """ Get optional file permissions if next arg is : """
                    if working_args[0] == Arg(':') and len(working_args) > 2:
                        working_args.pop(0)
                        file_permissions = working_args.pop(0).value
                    else:
                        file_permissions = 'rw-rw-rw-'
                    
                    """ Update the file system """
                    self.env.update_file_system(nam=file_name, contents=file_contents, permissions=file_permissions)

            elif Arg('dir') == args[0]:     # Set the working directory
                if len(args) > 2:
                    print('Invalid Number of arguments to state dir')
                else:
                    self.env.working_dir = str(args[1].value)
            
            elif Arg('stdin') == args[0]:   # Set STDIN via the env
                arg_text = ''
                for arg in args[1:]:
                    arg_text += str(arg.value)
                self.env.STDIO.write(arg_text)

            elif Arg('stdout') == args[0]:  # Set STDOUT via the env 
                arg_text = ''
                for arg in args[1:]:
                    arg_text += str(arg.value)
                self.env.STDIO.write(arg_text)
                self.end.transfer()
            
            else:                           # Pop an error if nothing happened
                print('Unkown argument: ' + str(args[0]) + ' passed to stateto state')
        
        """ Handle -p flag """
        if Flag('p') in flags or len(flags) == 0:
            self.env.showState()


    """ Nicely exits the CLI """
    def exit(self, flags):
        self.listening = False


    """ A simple function to not execute anything. Might be unnecessary but it exists """
    def void(self, flags, *args):
        pass


    """ How the judo interpreter handles history. Creates a new bpInterpreter with a copy of the
        old state so it can be updated. Could move the history maintanace to the bpInterpreter instead """
    def save_state(self):
        new_env = copy.deepcopy(self.env)
        self.history_stack += [ self.env ]
        self.env = new_env
    

    """ Implementation of the history command. Prints the history if -p is passed in.
        on/off/toggle will change if history is changed or not """
    def history(self, flags, *args):
        if Flag('p') in flags or len(flags) == 0:
            if len(self.history_stack):
                print("History")
                for i, time_step in enumerate(self.history_stack):
                    print('Level ', i, ': ')
                    time_step.showState(showFiles = False)
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
        alias = args[-1].value
        cmd_aliased = ' '.join( [ str(arg.value) for arg in args[:-1] ] ) # convert args to string
        self.parser.lexer.add_alias(alias, cmd_aliased)
