from bpInterpreterBase import InterpreterBase

class Record():
    def __init__(self, env, name, action = None):
        if type(env) is dict: env = InterpreterBase(**env)  # for json loading
        self.env = env 
        self.name = str(name)
        self.action = str(action)

    def print(self, showFiles = False):
        print('Name:', self.name)
        if self.action is not None:
            print('Action:', self.action)
        self.env.showState(showFiles = showFiles)
        print()

    def json(self):
        return {**{ 'name':str(self.name) },
            **{ "action":'' if self.action is None else str(self.action) }, 
            **{"env":self.env.json() } }
