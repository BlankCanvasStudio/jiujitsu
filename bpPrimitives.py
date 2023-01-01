from bpFileSystem import FileSocket, File


class ActionEntry():

    def __init__(self, func, text):
        self.func = func
        self.text = text

    def __call__(self):
        self.func()

    def __str__(self):
        return self.text 

    def __repr__(self):
        return self.__str__()


class State:
    def __init__(self, STDIO = FileSocket(id_num = 0), working_dir = '~', variables = {}, 
                    fs = {}, open_sockets = [], truths = {}):
        if type(STDIO) is dict: STDIO = FileSocket(**STDIO)
        if type(fs) is list:    # For json importing
            new_fs = {}
            for fd in fs:
                new_fs[fd['name']] = File(**fd)
            fs = new_fs
        for socket in open_sockets:
            if type(socket) is dict: socket = FileSocket(**socket)
        self.STDIO = STDIO
        self.working_dir = working_dir
        self.variables = variables
        self.fs = fs
        self.open_sockets = open_sockets
        self.truths = {}


    """ Print functionality for CLI (and I guess other purposes) """
    def show(self, showFiles = False):
        print('Working directory: ', self.working_dir, '\n')
        self.showVariables()
        print('Number of open sockets: ', len(self.open_sockets), '\n')
        print('Standard IN: ', self.STDIO.IN, '\n')
        print('Standard OUT: ', self.STDIO.OUT, '\n')
        self.showFileSystem(showFiles=showFiles)


    """ Update or create a file in the fs """
    def update_file_system(self, name,  contents, permissions, location = None):
        if location is None: location = self.working_dir
        self.fs[location + '/' + name] = File(name=name, contents=contents, permissions=permissions)


    """ Replace all the aliases possible in the state """
    def replace(self, nodes, replace_blanks = False):
        return bashparse.replace_variables(nodes, self.variables)


    """ Update the variables in the var list """
    def set_variable(self, name, value):
        if type(value) is not list: value = [ value ]
        self.variables[name] = value


    def update_variable_list(self, node):
        self.variables = bashparse.update_variable_list(node, self.variables)


    def json(self):
        open_socket_array = [ x.json() for x in self.open_sockets ]
        fs_array = [ x.json() for x in self.fs.values() ]
        return \
            {**{ "STDIO":self.STDIO.json() }, **{ "working_dir":self.working_dir },
            **{ "variables":self.variables }, **{"fs": fs_array}, 
            **{"open_sockets":open_socket_array}, **{ "truths":self.truths }}


    def showVariables(self):
        print('Variables: ')
        for key, value in self.variables.items():
            print('  ' + key + ': ' + value[-1])
        if not len(self.variables):
            print("No variables in list")
        print()


    def showFileSystem(self, showFiles = False):
        print('File System: ')
        for name, file in self.fs.items():
            print('  ' + name + ' permissions: ' + str(file.permissions))
            if showFiles:
                print(file.contents)
        if not len(self.fs):
            print("No Files in the file system")
        print()