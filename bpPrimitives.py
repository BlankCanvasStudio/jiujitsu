from bpFileSystem import FileSocket, File
import bashparser, copy


class ActionEntry():

    def __init__(self, func, text, args = None, code = None):
        self.func = func
        self.text = text
        self.args = args
        self.code = code

    def __call__(self):
        if self.args is not None:
            self.func(*self.args)
        else:
            self.func()

    def __str__(self):
        return self.text 

    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        return self.text == str(other)


class State:
    def __init__(self, STDIO = None, working_dir = None, variables = None, 
                    fs = None, open_sockets = None, truths = None):
        """ Irritating but necessary cause mutable arguemnts  """
        if STDIO is None: STDIO = FileSocket(id_num = 0)
        if working_dir is None: working_dir = '~'
        if variables is None: variables = {}
        if fs is None: fs = {}
        if open_sockets is None: open_sockets = []
        if truths is None: truths = {}

        """ Type checking stuff for json importing reasons """
        if type(STDIO) is dict: STDIO = FileSocket(**STDIO)
        if type(fs) is list:    # For json importing
            new_fs = {}
            for fd in fs:
                new_fs[fd['name']] = File(**fd)
            fs = new_fs
        for socket in open_sockets:
            if type(socket) is dict: socket = FileSocket(**socket)
        
        """ Finally actually doing the assignments """
        self.STDIO = STDIO
        self.working_dir = working_dir
        self.variables = variables
        self.fs = fs
        self.open_sockets = open_sockets
        self.truths = truths 

        """ Used when implementing subshells """
        self.starting_working_dir = working_dir
        self.STDIOS_above = []
        self.working_dirs_above = []
        self.variables_above = []


    def __eq__(self, other):
        if self.STDIO != other.STDIO: return False
        if self.working_dir != other.working_dir: return False 
        if self.variables != other.variables: return False
        if self.fs != other.fs: return False
        if len(self.open_sockets) != len(other.open_sockets): return False
        for i in range(0, len(self.open_sockets)):
            if self.open_sockets[i] != other.open_sockets[i]: return False
        if self.truths != other.truths: return False
        return True
    
    def __str__(self):
        return self.text(showFiles=False)
        

    def enter_subshell(self):
        # Save the info
        self.STDIOS_above += [ copy.deepcopy(self.STDIO) ]
        self.working_dirs_above += [ copy.deepcopy(self.working_dir) ]
        self.variables_above += [ copy.deepcopy(self.variables) ]
        # Create new info
        self.STDIO = FileSocket(id_num = 0)
        self.working_dir = self.starting_working_dir
        self.variables = {}

    def exit_subshell(self):
        if len(self.STDIOS_above):
            self.STDIO = self.STDIOS_above[-1]
            self.STDIOS_above = self.STDIOS_above[:-1]
        if len(self.working_dirs_above):
            self.working_dir = self.working_dirs_above[-1]
            self.working_dirs_above = self.working_dirs_above[:-1]
        if len(self.variables_above):
            self.variables = self.variables_above[-1]
            self.variables_above = self.variables_above[:-1]


    def text(self, showFiles = False):
        output = 'Working directory: ' + repr(self.working_dir) +'\n'
        output += self.variablesText() + '\n'
        output += 'Number of open sockets: ' + str(len(self.open_sockets)) + '\n'
        output += 'Standard IN: ' + repr(self.STDIO.IN) + '\n'
        output += 'Standard OUT: ' + repr(self.STDIO.OUT) + '\n'
        output += self.fileSystemText(showFiles=showFiles)
        return output


    """ Print functionality for CLI (and I guess other purposes) """
    def show(self, showFiles = False):
        print('Working directory: ', repr(self.working_dir), '\n')
        self.showVariables()
        print('Number of open sockets: ', len(self.open_sockets), '\n')
        print('Standard IN: ', repr(self.STDIO.IN), '\n')
        print('Standard OUT: ', repr(self.STDIO.OUT), '\n')
        self.showFileSystem(showFiles=showFiles)


    """ Update or create a file in the fs """
    def update_file_system(self, name,  contents, permissions='rw-rw-rw-', location = None):
        if location is None: location = self.working_dir
        # verify if path is absolute or not
        if not (name[0] == '~' or name[0] == '/'):
            if name[0:2] == './':
                name = name[2:]
            name = location + '/' + name
        # remove trailing slash
        if name[-1] == '/':
            name = name[:-1]
        # Actually update the file system
        self.fs[name] = File(name=name, contents=contents, permissions=permissions)


    """ Replace all the aliases possible in the state """
    def replace(self, nodes, replace_blanks = True):
        return bashparser.substitute_variables(nodes, self.variables, replace_blanks=replace_blanks)


    """ Update the variables in the var list """
    def set_variable(self, name, value):
        if type(value) is not list: value = [ value ]
        self.variables[name] = value


    def update_variable_list(self, node):
        self.variables = bashparser.update_variable_list(node, self.variables)


    def set_truth(self, name, value):
        if type(name) is not str: name = str(name)
        if type(value) is not bool: value = bool(value)
        self.truths[name] = value


    def test_truth(self, name):
        if type(name) is not str: name = str(name)
        if name not in self.truths:
            return None
        else:
            return self.truths[name]

    def json(self):
        open_socket_array = [ x.json() for x in self.open_sockets ]
        fs_array = [ x.json() for x in self.fs.values() ]
        return \
            {**{ "STDIO":self.STDIO.json() }, **{ "working_dir":self.working_dir },
            **{ "variables":self.variables }, **{"fs": fs_array}, 
            **{"open_sockets":open_socket_array}, **{ "truths":self.truths }}


    def showVariables(self):
        print(self.variablesText() + '\n')


    def variablesText(self):
        output = 'Variables: \n'
        for key, value in self.variables.items():
            if len(value):
                output += '  ' + key + ': "' + value[-1] + '"\n'
            else:
                # opting not to print variables with no values. LMK in an issue if that's wrong
                pass
        if not len(self.variables):
            output += "No variables in list\n"
        return output


    def showFileSystem(self, showFiles = False):
        print(self.fileSystemText(showFiles=showFiles) + '\n')


    def fileSystemText(self, showFiles = False):
        output = 'File System: \n'
        for name, file in self.fs.items():
            output += '  ' + name + ' permissions: ' + str(file.permissions) + '\n'
            if showFiles:
                output += file.contents + '\n'
        if not len(self.fs):
            output += "No Files in the file system" + '\n'
        return output
    
    def STDIN(self, IN=None):
        if IN is not None: 
            if type(IN) is bytes:
                self.STDIO.IN = IN.decode('utf-8')
            else:    
                self.STDIO.IN = str(IN)
        return self.STDIO.IN
    
    def STDOUT(self, OUT=None):
        if OUT is not None: 
            if type(OUT) is bytes:
                self.STDIO.OUT = OUT.decode('utf-8')
            else:    
                self.STDIO.OUT = str(OUT)
        return self.STDIO.OUT
    

    def copy_file(self, from_file, to_file):
        if from_file not in self.fs: self.fs[from_file] = File(name=from_file, contents='')
        self.fs[to_file] = self.fs[from_file]

    def remove_file(self, filename):
        if filename in self.fs:
            del self.fs[filename]
