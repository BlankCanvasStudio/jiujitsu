#!/bin/python3
from bpFileSystem import FileSocket, File
from bpInterpreterBase import InterpreterBase
import validators


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

    def f_echo(self, command, args, node):
        text = ''
        for node in args:
            text += node.word + ' '
        text = text[:len(text)-1]
        self.state.STDIO.write(text)

    def f_cd(self, command, args, node):
        if len(args) != 1: 
            print('bash: cd: too many arguments')
            self.state.STDIO.write('1')
        else: 
            self.working_dir = args[0].word
            self.state.STDIO.write('0')

    def f_wget(self, command, args, node):
        if validators.url(args[0].word): 
            filename = input('Wget requested "'+ args[0].word +'". Please enter a filename to pass in: ')
            file_contents = open(filename).read()
            self.update_file_system(name='index.html', contents=file_contents, permissions='rw-rw-rw-')
        else:
            raise ValueError(f"Invalid URL to wget: {args[0].word}")

    def f_chmod(self, command, args, node):
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

    def f_rm(self, command, args, node):
        if args[0].word in self.state.fs or self.state.working_dir+'/'+args[0].word in self.state.fs: self.state.fs.pop(args[0].word)
        else: print("rm: cannot remove '" + args[0].word + "': No such file or directory")

    def f_mv(self, command, args, node):
        self.state.copy_file(args[0].word, args[1].word)
        self.state.remove_file(args[0].word)
    
    def f_cp(self, command, args, node):
        self.state.copy_file(args[0].word, args[1].word)
    
    def f_(self, command, args, node):
        pass
