#!/bin/python3
import cmd, subprocess, os, sys, stat, copy, json, re, inspect, pathlib
import bashparser
try:
    from rich import print
except Exception:
    pass

from jiujitsu.jParser import Parser
from jiujitsu.jNode import Flag, Arg
from jiujitsu.bpInterpreter import Interpreter as bpInterpreter
from jiujitsu.bpFileSystem import FileSocket
from jiujitsu.jRecord import Record



class Interpreter(cmd.Cmd):

    def __init__(self, maintain_history = True, config_file = '~/.judo_config'):
        cmd.Cmd.__init__(self, 'tab')
        self.parser = Parser()
        self.prog_nodes = []
        self.index = 0
        self.index_history = [ 0 ]
        self.config_file = config_file
        self.env = bpInterpreter(STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {})
        self.history_stack = [ Record(env=self.env, name='init') ]
        self.alias_table = {}
        self.maintain_history = maintain_history
        # self.import_config(config_file)
        self.prompt = '\n>> '
        self.intro = 'Welcome to the Judo Shell!'

    def preloop(self):
        old_stdout = sys.stdout # backup current stdout
        sys.stdout = open(os.devnull, "w")
        self.import_config(self.config_file)
        sys.stdout = old_stdout

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        if cmd in self.alias_table:
            new_line = self.alias_table[cmd] + arg
            self.onecmd(new_line)
        else:
            print("Invalid command: " + cmd)


    def args_to_str(self, args, unescape=False):
        """ Converts arguments to strings. A necessary wrapper cause escape characters """
        text = ''
        for arg in args:
            if unescape:
                text += arg.unescape() + ' '
            else:
                text += arg.value + ' '
        if len(text):
            text = text[:-1]    # last space is wrong plz remove
        return text
    
    def get_next_node(self):
        # if self.prog_nodes is None or len(self.prog_nodes) == 0: return None
        if self.index >= len(self.prog_nodes): return None
        node = self.prog_nodes[self.index]
        return node

    def import_config(self, config_file = "~/.judo_config"):
        maintain_history = self.maintain_history      # So anything run in the config file doesn't generate a bunch of hist unless you specify
        self.maintain_history = False
        path = pathlib.Path(config_file).expanduser()
        if path.is_file():
            with open(path) as config_file:
                for new_line in config_file:
                    self.onecmd(new_line)
        self.maintain_history = maintain_history 


    def save_state(self, name = None, action = None):
        """ How the judo interpreter handles history. Creates a new bpInterpreter with a copy of the
        old state so it can be updated. Could move the history maintanace to the bpInterpreter instead """
        if name is None: name = str(len(self.history_stack))
        new_env = copy.deepcopy(self.env)
        self.history_stack += [ Record(env=new_env, name=name, action=action) ]
        self.env = new_env
        self.index_history += [ self.index ]


    def do_load(self, text):
        """ Loads a file to be iterated through with either next or inch commands 
            Takes an argument of a single filename 
            Add the -a flag to append the nodes to the current list 
            Add the -b flag to add the nodes to the beginning of the list
            If neither is specified, the list of program nodes will be reset """
        flags, args = self.parser.parse(text)
        filename = self.args_to_str(args)
        if not len(filename):
            print("Please specify a file to load")
            return
        path = pathlib.Path(filename).expanduser()
        if path.is_file():
            try:
                if Flag('a') in flags:
                    self.prog_nodes += bashparser.parse(open(path).read())
                    print('=> ' + str(bashparser.NodeVisitor(self.prog_nodes[0])))
                elif Flag('a') in flags:
                    self.prog_nodes = bashparser.parse(open(path).read()) + self.prog_nodes
                    print('=> ' + str(bashparser.NodeVisitor(self.prog_nodes[0])))
                else:
                    self.prog_nodes = bashparser.parse(open(path).read())
                    print('=> ' + str(bashparser.NodeVisitor(self.prog_nodes[0])))
                self.index = 0
            except Exception as e:
                print('bashparse failed to load file for the following reason: ')
                print(e)
        else:
            print('Cannot load file', filename, 'file not found')


    def do_next(self, text):
        """ Executes the next command in the node list. 
        Creates a save point if history is on
        Optional flags:
        -i build the command so you can call inch on it
        -e execute in surrounding env
        -p print the state of the system afterward
        -h save state in the history """
        flags, args = self.parser.parse(text)
        itrs = self.args_to_str(args)
        if not itrs.isdigit():
            itrs = 1
        else: itrs = int(itrs)
        for i in range(0, itrs):
            node = self.get_next_node()                         # Get the next node
            if not node and not len(self.env.action_stack): return print('No nodes left. Please load more')
            if Flag('i') not in flags:
                self.index = self.index + 1
            node_str = str(bashparser.NodeVisitor(node))

            """ All -e nodes need to be executed in environment so you can switch between them without issue """
            

            if not len(self.env.action_stack):
                if self.maintain_history or Flag('h') in flags:
                    self.save_state(action = node_str)
                
                if Flag('e') in flags:
                    self.do_shell(node_str)  # Convert to str then execute in real shell

                if Flag('i') in flags:  # i flag means you want to inch it
                    self.env.build(node, append = False)
                    if len(self.env.action_stack):
                        print('=>', self.env.action_stack[0])
                    else:
                        print('=> Action stack empty')
                else:
                    self.env.run(node)
            
            else:
                while len(self.env.action_stack): 
                    self.do_inch(text)

            if Flag('p') in flags:
                return self.state([])

            if self.get_next_node():
                print('=>', str(bashparser.NodeVisitor(self.get_next_node())))


    def do_undo(self, text):
        """ Undoes any action taken in the environment. Can't undo if no save point exists though.
            Use 'history on' or 'save <filename>' to create a save point """
        flags, args = self.parser.parse(text)

        if len(self.history_stack) > 1:                     # Roll back if possible
            # if self.env == self.history_stack[-1].env:
            self.history_stack = self.history_stack[:-1]
            self.index_history = self.index_history[:-1]
            self.env = self.history_stack[-1].env
            # self.index = self.index_history[-1]
            self.index  = self.index - 1
        else:                                               # If not the re-create from the ground up
            self.env = bpInterpreter()
            self.history_stack = [ Record(env=self.env, name='init') ]
            self.index = 0
            self.index_history = [ 0 ]
            self.import_config(self.config_file)


    def do_skip(self, text):
        """ Move passed a node if the user doesn't care about it """
         
        itrs = text 
        if not itrs.isdigit():
            itrs = 1
        else: itrs = int(itrs)
        
        for i in range(0, itrs):
            self.index = self.index + 1

    def do_save(self, name):
        """ Allows the user to create custom points in the history. Takes save point name as single argument """
        if not len(name):
            return print("Must specify a name for your save point. \nNothing was saved")

        action = 'User Save'
        self.save_state(name=name, action=action)


    def do_inch(self, text):
        """ If you have run the build command or next -i, the execution stack for the given command will be built, but not run. 
            The inch command then allows you to step through this action stack, allowing you to modify the state as the command 
            progresses.
            Use the -e flag to execute the command in the ACTUAL SYSTEM ENVIRONMENT. """
        
        if not len(self.env.action_stack):
            print("Action Stack is empty. Please run build or next/run -i to load the action stack")
            return
        
        flags, args = self.parser.parse(text)
        
        itrs = self.args_to_str(args)
        if not itrs.isdigit():
            itrs = 1
        else: itrs = int(itrs)
        
        for i in range(0, itrs):
            if Flag('e') in flags:
                node_str = self.env.action_stack[0].code 
                print('entered shell')
                if node_str:
                    self.do_shell(node_str)
                self.env.action_stack.pop(0)
                self.env.stdin('')

            else:
                res = self.env.inch()
            
            if len(self.env.action_stack):
                print(self.env.action_stack[0])
            else:
                print('Action stack empty')


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
        nodes = bashparser.parse(cmd)
        for node in nodes:
            self.env.run(node)

        
    def do_build(self, text):
        """ Builds the action stack for a given command. Useful for debugging the bashparser interpreter
            Use the -a flag to append the specified action to the action stack, rather than emptying it first """
        # Convert args to command
        flags, args = self.parser.parse(text)
        cmd = self.args_to_str(args)
        if not len(cmd) and not len(flags): return

        try:
            if Flag('f') in flags:  # f flag means you want to use the file, not the code passed in
                nodes = [ self.get_next_node() ]
            else:
                nodes = bashparser.parse(cmd)
        except:    
            print("bashlex could not build AST of code:")
            print(cmd)
        try:
            for node in nodes:
                self.env.build(node, append= Flag('a') in flags)
            if len(self.env.action_stack):
                print('=>', self.env.action_stack[0])
            else:
                print('=> Action stack empty')
        except:
            print('The interpreter cannot build the given command. Please report this bug')
        


    def do_stack(self, text):
        """ Prints the action stack of the interpreter """
        message = 'Action Stack: ' + '\n'
        output_array = self.env.stack().split('\n')
        for el in output_array:
            message += '  ' + str(el) + '\n'
        print(message)


    def do_parse(self, text):
        """ Nice little parse wrapper for bashparser.parse()
            Parses whatever text you pass into the function and dumps the node.
            Pass in the -f flag to parse the node at the current index in the file. """
        flags, args = self.parser.parse(text)
        text = self.args_to_str(args)
        if Flag('f') in flags:
            print(self.prog_nodes[self.index].dump())
        else:
            try:
                nodes = bashparser.parse(text)
                for node in nodes:
                    print(node.dump())
            except:
                print("bashlex could not build AST of code")
                # print(self.prog_nodes[self.index])


    def do_shell(self, text):
        """Runs a (real) command on your host system.  Note that the ! must be followed by a space.
                STDIO will be passed into the command unless the -n flag is specified """
        
        flags, args = self.parser.parse(text)
        text = self.args_to_str(args)
        
        self.env.shell(text, Flag('n') not in flags)
        
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
            on/off/toggle will change if history is saved automatically or not 
            -p flag will print the history
            -r flag with reset the history to the initial state """
        flags, args = self.parser.parse(text)

        if Flag('p') in flags or (len(flags) == 0 and len(args) == 0):
            output = '\n' + "History" + '\n'
            if len(self.history_stack):
                for record in self.history_stack: 
                    output += record.text(showFiles = False)
                    output += '---------------------\n\n\n'
            else:
                output += "No History yet\n"
            print(output)
        if Flag('r') in flags:
            print('at this point')
            self.env = bpInterpreter(STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {})
            self.history_stack = [ Record(env=self.env, name='init') ]
            self.import_config(self.config_file)
        if Arg('on') in args:
            self.maintain_history = True
        if Arg('off') in args:
            self.maintain_history = False
        if Arg('toggle') in args:
            self.maintain_history = not self.maintain_history


    def do_exit(self, text):
        "Quits the interpreter"
        exit()
    
    def do_quit(self, text):
        "Quits the interpreter"
        exit()


    def do_env(self, text):
        """ Used to switch environments or create environment files.
                Format: env -ea <filename>
                -e flag exports the environment file to the specified filename. If no file is specified, ~/.judo_config is overwritten
                -a appends the environment changes to the current environment, leaving currently defined variables in tack
                 """
        flags, args = self.parser.parse(text)

        if Flag('a') in flags: # Append to the state
            self.import_config(self.args_to_str(args))
        elif Flag('e') in flags:
            # This needs to export the path to a file
            output_text = ''
            
            # Need to do alias table
            for key, value in self.alias_table.items():
                output_text += 'alias ' + str(key) + ':' + str(value) + '\n'

            # Need to do interpreter itself
            output_text += 'stdin ' + self.env.stdin() + '\n'
            output_text += 'stdout ' + self.env.stdout() + '\n'
            output_text += 'dir ' + self.env.working_dir() + '\n'
            for key, value in self.env.state.variables.items():
                output_text += 'var ' + str(key) + ':' + ' '.join(value) + '\n'
            for value in self.env.state.fs.values():
                output_text += 'fs ' + value.name + ':' + value.contents + ':' + value.permissions + '\n'
            for key, value in self.env.state.truths.items():
                output_text += 'truth ' + str(key) + ':' + str(value) + '\n'

            # Put this last so it doesn't save a nunch of history by accident
            output_text += 'history on\n' if self.maintain_history else 'history off\n'

            filename = self.args_to_str(args)
            fd = open(filename, 'w')
            fd.write(output_text)

        else:
            self.__init__(config_file=self.args_to_str(args))


    def do_truth(self, text):
        """ Allows the user to assert statements to be true or false using the format <statement>:<bool>. 
            Useful for print statements
                Use the -p flag to print all current truths """
        flags, args = self.parser.parse(text)

        if Flag('p') in flags:
            for key, value in self.env.state.truths.items():
                print(key + ':' + str(value))
            if len(self.env.state.truths) == 0:
                print('No truths yet')

        old_truth = copy.copy(self.env.state.truths)
        while len(args):
            if len(args) < 3 or args[1] != Arg(':'):
                print('Invalid format for truth command. please use format truth <statement>:<Bool>')
                self.env.state.truths = old_truth
                return
            try:
                self.env.set_truth(args[0].value, args[2].value)
            except Exception as e:
                print(e)
                print('Invalid format for truth command. please use format truth <statement>:<bool>')
                self.env.state.truths = old_truth
                return
            args = args[3:]


    def do_list(self, text):
        """ Use to determine your location in a given bash script. Prints -5:+5 lines around the current line.
            you can print custom ranges by passing -X:+Y to the function """
        if len(self.prog_nodes) == 0:
            print('No nodes currently loaded')
            return

        flags, args = self.parser.parse(text)
        if len(args) == 0:
            args = [ Arg('-5'), Arg(':'),  Arg('+5')]
        elif len(args) > 3:
            print('Invalid arguments to list. Please use the format: list -X:+Y')
            return
        
        neg = int(args[0].value) if int(args[0].value) < 0 else -int(args[0].value)
        pos = int(args[2].value)

        current_index = self.index + neg if self.index + neg >= 0 else 0
        
        while current_index < len(self.prog_nodes) and current_index <= self.index + pos:
            if current_index == self.index:
                print(str(current_index), '=>', '\t', str(bashparser.NodeVisitor(self.prog_nodes[current_index])) )
            else:
                print(str(current_index), '\t', str(bashparser.NodeVisitor(self.prog_nodes[current_index])) )
            
            current_index += 1
        
        if self.index >= len(self.prog_nodes):
            print('=>', '\t', 'FIN')



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
    

    def do_reset(self, text):
        """ Resets the enironment to the original state """
        self.__init__(maintain_history = self.maintain_history, config_file = self.config_file)

    def do_screen(self, text):
        """ Allows users to interact with a virtual 'screen' which logs the culumative outputs of all the functions called.
            Pass the -p flag or no flags to print the screen. 
            Pass the -c flag to clear the screen """
        flags, args = self.parser.parse(text)
        
        if Flag('p') in flags or len(flags) == 0:
            print(self.env.get_screen())
        if Flag('c') in flags:
            self.env.clear_screen()

    
def main():
    Interpreter().cmdloop()


if __name__ == '__main__':
    main()
