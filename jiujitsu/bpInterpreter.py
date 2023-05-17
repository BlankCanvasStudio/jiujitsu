#!/bin/python3
from jiujitsu.bpFileSystem import FileSocket, File
from jiujitsu.bpInterpreterBase import InterpreterBase
import validators
import bashparser


class Interpreter(InterpreterBase):

    def __init__(self, STDIO = None, working_dir = None, variables = None, 
                    fs = None, open_sockets = None, truths = None):
        
        """ Irritating but necessary cause mutable arguments """
        if STDIO is None: STDIO = FileSocket(id_num = 0)
        if working_dir is None: working_dir = '~'
        if variables is None: variables = {}
        if fs is None: fs = {}
        if open_sockets is None: open_sockets = []
        if truths is None: truths = {}

        super().__init__(STDIO=STDIO, working_dir=working_dir, variables=variables, 
                            fs=fs, open_sockets=open_sockets, truths=truths)

    def f_echo(self, node):
        command, args = self.parse_node(node)
        text = ''
        for node in args:
            if node.kind != 'word': break
            text += node.word + ' '
        text = text[:len(text)-1]
        self.state.STDIO.write(text)

    def f_cd(self, node):
        command, args = self.parse_node(node)
        if len(args) != 1: 
            print('bash: cd: too many arguments')
        else: 
            self.state.working_dir = args[0].word

    def f_wget(self, node):
        command, args = self.parse_node(node)
        if validators.url(args[0].word): 
            added = False
            while not added:
                try: 
                    filename = input('Wget requested "'+ args[0].word +'". Please enter a filename to pass in: ')
                    file_contents = open(filename).read()
                    self.update_file_system(name='index.html', contents=file_contents, permissions='rw-rw-rw-')
                    added = True
                except:
                    print('Unable to load file. Please try again')
        else:
            print(f"Invalid URL to wget: {args[0].word}")

    def f_chmod(self, node):
        command, args = self.parse_node(node)
        if args[0].word == '+x':
            location = self.state.working_dir + '/' + args[1].word        # This actually doesn't work
            if location in self.state.fs: 
                permissions = self.state.fs[location].permissions
            else: 
                permissions = 'rw-rw-rw-'
                self.state.fs[location] = File(name=args[1].word, contents=None, permissions=permissions)
            perm_list = list(permissions)
            perm_list[2] = 'x'
            perm_list[5] = 'x'
            perm_list[8] = 'x'
            permissions = ''.join(perm_list)
            self.state.fs[location].setPermissions(permissions)

    def f_rm(self, node):
        command, args = self.parse_node(node)
        flags = []
        documents = []
        for arg in args:
            if arg.word[0] == '-': 
                flags += [ arg ]
            else:
                documents += [ arg ]
        if documents[0].word == '/': self.state.fs = {}
        elif documents[0].word in self.state.fs or self.state.working_dir+'/'+documents[0].word in self.state.fs: self.state.fs.pop(documents[0].word)
        else: print("rm: cannot remove '" + documents[0].word + "': No such file or directory")

    def f_mv(self, node):
        command, args = self.parse_node(node)
        self.state.copy_file(args[0].word, args[1].word)
        self.state.remove_file(args[0].word)
    
    def f_cp(self, node):
        command, args = self.parse_node(node)
        self.state.copy_file(args[0].word, args[1].word)
    
    def f_unset(self, node):
        # Unset variables first, the functions, allow for -f flag and -n flag. They are mutually exclusive
        command, args = self.parse_node(node)

        if args[0].word == '-f':
            for arg in args[1:]:
                self.state.unset_functions(arg.word)
        elif args[0].word == '-n':
            print('-n flag not implemented')
        else:
            for arg in args:
                if not self.state.unset_varibles(arg.word):
                    self.state.unset_functions(arg.word)
    
    def f_shift(self, node):
        self.state.shift_variables()

    def f_bash(self, node):
        command, args = self.parse_node(node)
        sub_cmd = ' '.join([ str(bashparser.NodeVisitor(x)) for x in args ])
        sub_node = bashparser.parse(sub_cmd)[0]
        self.state.enter_subshell()
        self.run(sub_node)

    def f_(self, node):
        pass

