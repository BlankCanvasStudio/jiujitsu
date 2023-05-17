from unittest import TestCase

from jiujitsu import State, File, FileSocket

import bashparser

class TestState(TestCase):
    def test_init(self):
        stdio = FileSocket(id_num = 1)
        working_dir = '~/some/where'
        variables = {
            'name1':['value1'],
            'name2':['value2', 'value3']
        }
        # Test loading the state from a json #
        fs = [
            { 
                "name": "~/name1",
                "contents": "value1",
                "permissions": "rw-rw-rw-"
            }
        ]
        # Actual fs form #
        fs2 = {
            "~/name1": File("~/name1", "value1", "rw-rw-rw-")
        }
        open_socket = []
        truths = {
            'something':True,
            'else':False,
        }
        new_state = State(STDIO=stdio, working_dir=working_dir, variables=variables, 
                        fs=fs, open_sockets=open_socket, truths=truths)
        
        self.assertTrue(new_state.STDIO == stdio)
        self.assertTrue(new_state.working_dir == working_dir)
        self.assertTrue(new_state.variables == variables)
        self.assertTrue(new_state.fs == fs2)    # Verify the file has been unpacked correctly
        self.assertTrue(new_state.open_sockets == open_socket)
        self.assertTrue(new_state.truths == truths)


        # Verify not unpacking fs also works #
        new_state2 = State(STDIO=stdio, working_dir=working_dir, variables=variables, 
                        fs=fs2, open_sockets=open_socket, truths=truths)
        self.assertTrue(new_state2.STDIO == stdio)
        self.assertTrue(new_state2.working_dir == working_dir)
        self.assertTrue(new_state2.variables == variables)
        self.assertTrue(new_state2.fs == new_state.fs)    # Verify the file has been unpacked correctly
        self.assertTrue(new_state2.open_sockets == open_socket)
        self.assertTrue(new_state2.truths == truths)


    def test_update_file_system(self):
        # This should mirror test_bpInterpreterBase.test_update_file_system #
        stdio = State()
        
        # Try it with all arguments #
        stdio.update_file_system('name1', 'contents1', permissions='rwxrw-rw-', location='~/new/place')
        self.assertTrue(stdio.fs['~/new/place/name1'] == File('~/new/place/name1', 'contents1', 'rwxrw-rw-'))


        # Try it without location #
        stdio.update_file_system('name2', 'contents2', permissions='rwxrw-rw-')
        self.assertTrue(stdio.fs['~/name2'] == File('~/name2', 'contents2', 'rwxrw-rw-'))

        # Try it without permissions #
        stdio.update_file_system('name3', 'contents3')
        self.assertTrue(stdio.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))

        # Update a file already in the file system #
        stdio.update_file_system('name3', 'contents4')
        self.assertTrue(stdio.fs['~/name3'] == File('~/name3', 'contents4', 'rw-rw-rw-'))

        # Verify ./ gets replaced properly #
        stdio.update_file_system('./name4', 'contents4')
        self.assertTrue(stdio.fs['~/name4'] == File('~/name4', 'contents4', 'rw-rw-rw-'))

        # Verify trailing slash gets removed properly #
        stdio.update_file_system('./name5/', 'contents5')
        self.assertTrue(stdio.fs['~/name5'] == File('~/name5', 'contents5', 'rw-rw-rw-'))


    def test_replace(self):
        # Most of the replacement testing is actually in bashparser #
        # This should mirror test_bpInterpreterBase.test_replace #
        var_list = {'one':['two']}
        stdio = State(variables=var_list)
        node = bashparser.parse("echo $one")
        replaced = stdio.replace(node)
        self.assertTrue(replaced[0] == bashparser.parse('echo two')[0])

        # Thanks Wes for finding this bug #
        node = bashparser.parse("echo a; b=3; echo $b")
        replaced = stdio.replace(node, full=True)
        self.assertTrue(replaced[0] == bashparser.parse('echo a; b=3; echo 3')[0])


    def test_set_variable(self):
        stdio = State()
        # Make sure it gets wrapped in an array #
        stdio.set_variable('name', 'value1')
        self.assertTrue(stdio.variables['name'] == ['value1'])

        # Verify the default case #
        stdio.set_variable('name2', ['value2', 'value3'])
        self.assertTrue(stdio.variables['name2'] == ['value2', 'value3'])


    def test_update_variable_list(self):
         stdio = State()
         node = bashparser.parse('a=b')[0]
         stdio.update_variable_list(node)
         self.assertTrue(stdio.variables['a'] == ['b'])


    def test_json(self):
        something = State()
        json = something.json()

        self.assertTrue(json['STDIO'] == FileSocket(id_num=0).json())
        self.assertTrue(json['working_dir'] == '~')
        self.assertTrue(json['variables'] == {})
        self.assertTrue(json['fs'] == [])
        self.assertTrue(json['open_sockets'] == [])
        self.assertTrue(json['truths'] == {})
    

    def test_set_truth(self):
        state = State()

        state.set_truth('something', True)
        self.assertTrue(state.test_truth('something'))


    def test_test_truth(self):
        state = State()

        self.assertTrue(state.test_truth('something') == None)

        state.set_truth('something', True)
        self.assertTrue(state.test_truth('something'))

        state.set_truth('something', False)
        self.assertTrue(not state.test_truth('something'))
    

    def test_STDIN(self):
        state = State()
        
        state.STDIN('something')
        self.assertTrue(state.STDIO.IN == 'something')

        state.STDIN(b'else')
        self.assertTrue(state.STDIO.IN == 'else')
    

    def test_STDOUT(self):
        state = State()
        
        state.STDOUT('something')
        self.assertTrue(state.STDIO.OUT == 'something')

        state.STDOUT(b'else')
        self.assertTrue(state.STDIO.OUT == 'else')
