import cmd, subprocess, os, stat, copy, json, re, inspect
import bashparse
try:
    from rich import print
except Exception:
    pass

from jParser import Parser
from jNode import Flag, Arg
from bpInterpreter import Interpreter as bpInterpreter
from bpFileSystem import FileSocket
from jRecord import Record






class Interpreter(cmd.Cmd):

    def __init__(self, maintain_history = True):
        cmd.Cmd.__init__(self, 'tab')
        self.parser = Parser()
        self.prog_nodes = None
        self.index = 0
        self.maintain_history = maintain_history
        self.env = bpInterpreter(STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {})
        self.history_stack = [ Record(env=self.env, name='init') ]
        self.alias_table = {}
    

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
    

    def save_state(self, name = None, action = None):
        """ How the judo interpreter handles history. Creates a new bpInterpreter with a copy of the
        old state so it can be updated. Could move the history maintanace to the bpInterpreter instead """
        if name is None: name = str(len(self.history_stack))
        new_env = copy.deepcopy(self.env)
        self.history_stack += [ Record(env=new_env, name=name, action=action) ]
        self.env = new_env


    def postcmd(self, stop, line):
        print()


    def do_load(self, filename):
        """ Loads a file to be iterated through with either next or inch commands 
            Takes an argument of a single filename """
        if not len(filename):
            print("Please specify a file to load")
            return
        self.prog_nodes = bashparse.parse(open(filename).read())
        self.index = 0


    def do_next(self, text):
        """ Executes the next command in the node list. 
        Creates a save point if history is on
        Optional flags:
        -i build the command so you can call inch on it
        -e execute in surrounding env
        -p print the state of the system afterward
        -h save state in the history """
        flags, args = self.parser.parse(text)

        def get_next_node():
            # if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
            if self.index > len(self.prog_nodes) - 1: return None
            node = self.prog_nodes[self.index]
            self.index = self.index + 1
            return node

        node = get_next_node()                         # Get the next node
        if not node: return print('No nodes left. Please load more')
        node_str = str(bashparse.NodeVisitor(node))

        """ All -e nodes need to be executed in environment so you can switch between them without issue """
        if self.maintain_history or Flag('h') in flags:
            self.save_state(action = node_str)

        if Flag('e') in flags:
            self.do_shell(node_str)  # Convert to str then execute in real shell

        if Flag('i') in flags:  # i flag means you want to inch it
            self.env.build(node, append = False)
        else:
            self.env.run(node)

        if Flag('p') in flags:
            return self.state([])


    def do_undo(self, text):
        """ Undoes any action taken in the environment. Can't undo if no save point exists though.
            Use 'history on' or 'save <filename>' to create a save point """
        flags, args = self.parser.parse(text)

        if len(self.history_stack) > 1:                     # Roll back if possible
            self.history_stack = self.history_stack[:-1]
            self.env = self.history_stack[-1].env
            self.index  = self.index - 1
        else:                                               # If not the re-create from the ground up
            self.env = bpInterpreter()
            self.history_stack = [ Record(env=self.env, name='init') ]
            self.index = 0


    def do_skip(self, text):
        """ Move passed a node if the user doesn't care about it """
        self.index = self.index + 1
    

    def do_save(self, name):
        """ Allows the user to create custom points in the history. Takes save point name as single argument """
        if not len(name):
            return print("Must specify a name for your save point. \nNothing was saved")

        action = 'User Save'
        self.save_state(name=name, action=action)


    def do_inch(self, text):
        """  """
        res = self.env.inch()
        if not res:
            print("Action Stack is empty. Please run build or next/run -i to load the action stack")


    def do_run(self, text):
        """ Run a user input command by combining the args into a command and executing it. 
        All commands must also be run in env to maintain consistency. -i is a wrapper for build """
        flags, args = self.parser.parse(text)
        cmd = self.args_to_str(args)

        if self.maintain_history or Flag('h') in flags:
            self.save_state(action = cmd)
        if Flag(value='e') in flags: 
            self.do_shell(cmd)
        
        """ Adding -i is going to be a wrapper for build so it mirrors 'next' nicely """
        if Flag(value='i') in flags:
            self.do_build(self.args_to_str(args))
            return
        
        """ Even escaped commands must be run in env to maintain consistency when switching """
        nodes = bashparse.parse(cmd)
        for node in nodes:
            self.env.run(node)


        
    def do_build(self, text):
        """ Builds the action stack for a given command. Useful for debugging the bashparse interpreter
            Use the -a flag to append the specified action to the action stack, rather than emptying it first """
        # Convert args to command
        flags, args = self.parser.parse(text)
        cmd = self.args_to_str(args)

        # Build the action stack for the node
        try:
            nodes = bashparse.parse(cmd)
            for node in nodes:
                self.env.build(node, append= Flag('a') in flags)
        except:
            print("Bashparse cannot parse the code provided")


    def do_stack(self, text):
        """ Prints the action stack of the interpreter """
        message = 'Action Stack: ' + '\n'
        output_array = self.env.stack().split('\n')
        for el in output_array:
            message += '  ' + str(el) + '\n'
        print(message)


    def do_parse(self, text):
        """ Nice little parse wrapper for bashparse.parse()
            Parses whatever text you pass into the function and dumps the node """
        try:
            nodes = bashparse.parse(text)
            for node in nodes:
                print(node.dump())
        except:
            print("Bashparse could not parse text")
    

    def do_shell(self, text):
        "Runs a (real) command on your host system.  Note that the ! must be followed by a space."
        nodes = self.env.replace(bashparse.parse(text))
        
        """ Convert the replaced nodes to text """
        text = ' '.join( [ str(bashparse.NodeVisitor(x)) + '\n' for x in nodes ] )
        
        """ Execute the code """
        result = subprocess.run(text, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        """ Put results in the STDIO """
        output = str(result.stdout)
        if len(str(result.stderr)): output += '\n' + 'Error: ' + str(result.stderr)
        self.env.state.STDIO.OUT = output


    def do_dir(self, text):
        """ Deals with the printing and modificaiton of the interpreters working directory """
        flags, args = self.parser.parse(text)   # Do it this way cause escaping
        if len(args) == 1:
            self.env.working_dir(args[0].value)
            print('Working dir: ' + self.env.working_dir())
        else : 
            print("Invalid number of arguments passed into DIR. Nothing changed")


    def do_stdin(self, text):
        """ Updates stdin to passed in value. Prints STDIN, regardless of if value is passed in or not """
        if len(text):
            self.env.stdin(text)
        print("STD IN: " + self.env.stdin())


    def do_stdout(self, text):
        """ Updates stdout to passed in value. Prints STDOUT, regardless of if value is passed in or not """
        if len(text):
            self.env.stdout(text)
        print("STD OUT: " + self.env.stdout())


    def do_var(self, text):
        """ For maintaining the variables in the current env
            Takes arguments of the format <name:value> """
        flags, args = self.parser.parse(text)
        if len(args):
            """ Save the name:value combo from args until args is empty """
            while len(args) >= 3 and args[1] == Arg(':'):    # Man I hate this implementation
                self.env.set_variable(args[0].value, args[2].value) # Name:Value
                args = args[3:] if len(args) > 3 else []

        if Flag('p') in flags:
            print(self.env.text_variables())

    
    def do_fs(self, text):
        """ Adds files to the file system using the format name:contents:permissions.
            Permissions optional with default rw-rw-rw- 
            Pass the -p flag to print the file system """
        
        flags, args = self.parser.parse(text)

        working_args = list(args)
        """ Strip out name:contents and name:contents:permissions, then save to env """
        while len(working_args):
            """ Strip the filename """
            file_name = working_args.pop(0).value

            """ Strip the : """
            if working_args[0] != Arg(':'): 
                print('Invalid file formation. Please follow pattern: name:contents:permissions')
                return
            working_args.pop(0)

            """ Get the file contents """
            if not len(working_args): 
                print('Invalid file formation. File contents needed')
                return
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
            print(self.env.text_filesystem(showFiles=True))


    def do_state(self, text):
        """ Implementation of the state function. Prints if the -p flag is passed in """
        output = '\n' + self.env.stateText()
        print(output)


    def do_void(self, text):
        """ A simple function to not execute anything. Might be unnecessary but it exists """
        pass


    def do_history(self, text):
        """ Implementation of the history command. Prints the history if -p is passed in.
        on/off/toggle will change if history is saved automatically or not """
        flags, args = self.parser.parse(text)

        if Flag('p') in flags or len(flags) == 0:
            output = '\n' + "History" + '\n'
            if len(self.history_stack):
                for record in self.history_stack: output += record.text(showFiles = False)
            else:
                output += "No History yet\n"
            print(output)
        if Arg('on') in args:
            self.maintain_history = True
        if Arg('off') in args:
            self.maintain_history = False
        if Arg('toggle') in args:
            self.maintain_history = not self.maintain_history


    def do_quit(self, flags, *args):
        "Quits the interpreter"
        exit()


    def do_tokenize(self, text):
        """ Prints the flags and arguments parsed from a given judo command.
            Used primarily for debugging """
        flags, args = self.parser.parse(text)
        print('flags: ', flags)
        print('args: ', args)
    

    def do_alias(self, text):
        """ Takes the form: alias <name> <text>
            Anytime <name> is used as a command, the aliased text is replace and the new command is executed. 
            <name> can only be a single word, without spaces.
            alias -p <name> prints the corresponding entry in the alias table
            alias -a prints the entire alias table """
        flags, args = self.parser.parse(text)
       
        if Flag('p') in flags:
            output = ''
            for el in args:
                output += el.value + ': ' + self.alias_table[el.value] + '\n'
            print(output)
        elif Flag('a') in flags:
            print('Alias Table:')
            for name, text in self.alias_table.items():
                print('  ' + name + ': ' + text)
        else:
            alias_name = args[0].value
            alias_text = self.args_to_str(args[1:])
            self.alias_table[alias_name] = alias_text
    
    
    def default(self, line):
        cmd, arg, line = self.parseline(line)
        if cmd in self.alias_table:
            new_line = self.alias_table[cmd] + arg
            self.onecmd(new_line)
        else:
            print("Invalid command: " + cmd)


if __name__ == '__main__':
    Interpreter().cmdloop()
