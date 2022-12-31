class File:
    def __init__(self, name, contents, permissions = 'rw-rw-rw-'):
        self.name = name
        self.contents = contents
        self.permissions = permissions

    def __str__(self):
        print('FileName: ', self.name)
        print('  Permissions: ', self.permissions)
        print('  Contents: ', self.contents)
    
    def setPermissions(self, permissions):
        self.permissions = permissions


class FileSocket:
    def __init__(self, id_num, working_dir = '~'):
        self.OUT = ''
        self.id = id_num
        self.IN = ''

    def write(self, text_in):
        self.OUT += text_in 

    def read(self):
        tmp = self.IN
        self.IN = ''
        return tmp

    def transfer(self):
        self.IN = self.OUT
        self.OUT = ''
    
    def peek(self):
        return self.IN
