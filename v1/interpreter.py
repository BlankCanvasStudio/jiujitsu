import functools
open_sockets = []

class FileSocket:
    def __init__(self):
        self.OUT = ''
        global open_sockets
        self.id = len(open_sockets)
        self.IN = ''
        open_sockets += [ self ]
    
    def write(self, text_in):
        self.OUT += text_in 
    
    def read(self):
        tmp = self.IN
        self.IN = ''
        return tmp
    
    def transfer(self):
        self.IN = self.OUT
        self.OUT = ''

STDIO = FileSocket()


class Echo:
    def __init__(self, text):
        self.text = text
    
    def __call__(self):
        global STDIO
        STDIO.write(self.text)


def f_command(p):
    name = p[1][0].word
    args = p[1][1:]
    if name == 'echo':
        text = ' '.join([ x.word for x in args ])
        p[0].command = Echo(text)
    else:
        raise ValueError("Function call " + name + " not implemented")


def f_pipeline_command(p):
    class Run:
        def __init__(self, parts):
            self.parts = parts
        def __call__(self):
            for i, part in enumerate(self.parts):
                if i % 2 == 0:
                    try:
                        part.command()
                        if i != len(self.parts) - 1:
                            STDIO.transfer()
                    except:
                        print('failed for: ', part)
            print(STDIO.OUT)    # Print the STDOUT if its the last command
    
    if not (len(p) == 2 and len(p[1]) == 1):
        p[0].command = Run(p[0].parts)


def f_simple_list(p):
    class Run:
        def __init__(self, parts):
            self.parts = parts
        def __call__(self):
            if type(self.parts) == list:
                for i, part in enumerate(self.parts):
                    if i % 2 == 0:
                        part.command()
                
            else:
                print(' in THIS')
                self.parts.command()
                print('command: ', self.parts.command)
            print(STDIO.OUT)  # Print the STDOUT if its the last command

    if p[0].kind == 'pipeline':
        p[0].command = Run(p[0].parts)
    if p[0].kind == 'command':
        print('p0: ', p[0])
        print('p1: ', p[1])
        p[0].command = Run(copy.deepcopy(p[0]))


"""
def f_simple_command_element(p):
    print('p: ', p[0])
"""
