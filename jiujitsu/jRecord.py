from jiujitsu.bpInterpreterBase import InterpreterBase

class Record():
    def __init__(self, env, name, action = None):
        if type(env) is dict: env = InterpreterBase(**env)  # for json loading
        self.env = env 
        self.name = str(name)
        self.action = str(action)
    
    def __eq__(self, other):
        if self.env != other.env: return False
        if self.name != other.name: return False
        if self.action != other.action: return False
        return True

    def print(self, showFiles = False):
        print('Name:', self.name)
        if self.action is not None:
            print('Action:', self.action)
        self.env.showState(showFiles = showFiles)
        print()
    
    def text(self, showFiles = False):
        output = 'Name:' + self.name + '\n'
        if self.action is not None:
            output += 'Action:' + self.action + '\n'
        output += self.env.stateText(showFiles = showFiles) + '\n'
        return output

    def json(self):
        return {**{ 'name':str(self.name) },
            **{ "action":'' if self.action is None else str(self.action) }, 
            **{"env":self.env.json() } }
