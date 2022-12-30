class Record():
    def __init__(self, env, name, action = None):
        self.env = env 
        self.name = name
        self.action = action

    def print(self, showFiles = False):
        print('Name:', self.name)
        if self.action is not None:
            print('Action:', self.action)
        self.env.showState(showFiles = showFiles)
        print()

