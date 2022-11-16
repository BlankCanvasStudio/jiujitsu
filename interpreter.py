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
            for i, part in enumerate(self.parts):
                if i % 2 == 0:
                    part.command()
            print(STDIO.read())  # Print the STDOUT if its the last command
    
    p[0].command = Run(p[0].parts)

