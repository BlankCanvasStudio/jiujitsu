open_sockets = []

class FileSocket:
    def __init__(self):
        self.text = ''
        global open_sockets
        self.id = len(open_sockets)
        open_sockets += [ self ]
    def write(self, text_in):
        self.text += text_in 
    def read(self):
        tmp = self.text
        self.text = ''
        return tmp

STDIO = FileSocket()


def echo(text):
    global STDIO
    STDIO.write(text)


def f_command(p):
    name = p[1][0].word
    args = p[1][1:]
    if name == 'echo':
        text = ' '.join([ x.word for x in args ])
        echo(text)
    else:
        raise ValueError("Function call " + name + " not implemented")
    #print('node: ', p[0])
    #p[0] = 'testing'
    # If its at the top level, make sure the final action is to print the STDIO to screen
    # if (p[0].kind == 'command'): print('command: ', STDIO.read())


def f_pipeline(p):
    #print('p: ', p[0])
    #print('stdio: ', STDIO.text)
    # if (p[0].kind == 'pipeline'): print('pipeline: ', STDIO.read())
    if len(p) == 2:
        pass
    else:
        print('final p0: ', p[0])
        print('actual p1: ', p[1])
        print('p extend: ', p[len(p) - 1])
        print('\n\n\n')
        # p[0].results = ( p[1].results | None ) | (p[len(p) - 1].results | None)

"""
def f_list(p):
    # If its at the top level, make sure the final action is to print the STDIO to screen
    if (p[0].kind == 'list'): print('list: ', STDIO.read())

def f_compound_list(p):
    # If its at the top level, make sure the final action is to print the STDIO to screen
    if (p[0].kind == 'compound_list'): print('compound_list: ', STDIO.read())

def f_inputunit(p):
    print('in the input unit')
"""
