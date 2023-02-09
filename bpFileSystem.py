class File:
    def __init__(self, name, contents, permissions = 'rw-rw-rw-'):
        self.name = name
        self.contents = contents
        self.permissions = permissions

    def __str__(self):
        return 'FileName: ' + self.name + '\n' \
                + '  Permissions: ' + self.permissions + '\n' \
                + '  Contents: ' + self.contents
    
    def __eq__(self, other):
        if self.name != other.name: return False
        if self.contents != other.contents: return False
        if self.permissions != other.permissions: return False
        return True

    def setPermissions(self, permissions):
        self.permissions = permissions
    
    def json(self):
        return { 'name':str(self.name), 'contents':str(self.contents), 'permissions':str(self.permissions) }


class FileSocket:
    def __init__(self, id_num, IN = '', OUT = ''):
        self.OUT = OUT
        self.id = id_num
        self.IN = IN
    
    def __eq__(self, other):
        if self.OUT != other.OUT: return False
        if self.id != other.id: return False
        if self.IN != other.IN: return False
        return True

    def write(self, text_in):
        if type(text_in) is bytes:
            self.OUT += text_in.decode('utf-8')
        else:
            self.OUT += str(text_in)
        return self.OUT 

    def read(self):
        tmp = self.IN
        self.IN = ''
        return tmp

    def transfer(self):
        self.IN = self.OUT
        self.OUT = ''
    
    def peek(self):
        return self.IN
    
    def json(self):
        return {
            "IN": self.IN, 
            "OUT": self.OUT, 
            "id_num": self.id,
        }
