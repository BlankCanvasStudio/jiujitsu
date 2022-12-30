from bpFileSystem import FileSocket


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

        self.STDIO = STDIO
        self.working_dir = working_dir
        self.variables = variables
        self.fs = fs
        self.open_sockets = open_sockets
        self.truths = {}
    

    """ Print functionality for CLI (and I guess other purposes) """
    def show(self, showFiles = False):
        print('Interpreter State: ')
        print('Working directory: ', self.working_dir)
        print('Variables: ')
        for key, value in self.variables.items():
            print('  ' + key + ': ' + value[-1])
        print('Number of open sockets: ', len(self.open_sockets))
        print('Standard IN: ', self.STDIO.IN)
        print('Standard OUT: ', self.STDIO.OUT)
        print('File System: ')
        for name, file in self.fs.items():
            print('  ' + name + ' permissions: ' + str(file.permissions))
            if showFiles:
                print(file.contents)
    

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