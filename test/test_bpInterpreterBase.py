from unittest import TestCase
from bpInterpreterBase import InterpreterBase, InterpreterError
from bpInterpreter import Interpreter as Full_Interpreter
from bpPrimitives import State
from bpFileSystem import File, FileSocket
import bashparse

class TestBpInterpreterBase(TestCase):

    def test_init(self):
        """ Verify all the objects are created correctly with no arguments """
        intr = InterpreterBase()
        state = State()
        self.assertTrue(intr.state == state)
        self.assertTrue(intr.action_stack == [])
        self.assertTrue(intr.execute == True)

        """ Verify the passed in arguments work well """
        stdio = FileSocket(id_num = 1)
        working_dir = '~/some/where'
        variables = {
            'name1':['value1'],
            'name2':['value2', 'value3']
        }
        """ Test loading the state from a json """
        fs = [
            { 
                "name": "~/name1",
                "contents": "value1",
                "permissions": "rw-rw-rw-"
            }
        ]
        """ Actual fs form """
        fs2 = {
            "~/name1": File("~/name1", "value1", "rw-rw-rw-")
        }
        open_socket = []
        truths = {
            'something':True,
            'else':False,
        }
        intr = InterpreterBase(stdio, working_dir, variables, fs, open_socket, truths, execute=False)
        expected_state = State(stdio, working_dir, variables, fs, open_socket, truths)
        self.assertTrue(intr.state == expected_state)
        self.assertTrue(intr.execute == False)
        self.assertTrue(intr.action_stack == [])

        intr = InterpreterBase(stdio, working_dir, variables, fs2, open_socket, truths, execute=True)
        expected_state2 = State(stdio, working_dir, variables, fs2, open_socket, truths)
        self.assertTrue(intr.state == expected_state2)
        self.assertTrue(intr.execute == True)
        self.assertTrue(intr.action_stack == [])
        self.assertTrue(intr.state.fs == expected_state.fs)


    def test_json(self):
        """ Only need to verify execute wraps properly. state is checked in bpPrimatives """
        intr = InterpreterBase(execute = False)
        self.assertTrue(intr.json()['execute'] == 'f')
        intr = InterpreterBase(execute = True)
        self.assertTrue(intr.json()['execute'] == 't')


    def test_working_dir(self):
        intr = InterpreterBase()
        self.assertTrue(intr.working_dir() == '~')
        self.assertTrue(intr.working_dir('~/some/where') == '~/some/where')


    def test_update_file_system(self):
        """ This should mirror test_bpPrimitives.test_update_file_system """
        intr = InterpreterBase()

        self.assertRaises(InterpreterError, intr.update_file_system, 1234, 'contents')
        self.assertRaises(InterpreterError, intr.update_file_system, 'name', 1234)
        self.assertRaises(InterpreterError, intr.update_file_system, 'name', 'contents', 1234)
        self.assertRaises(InterpreterError, intr.update_file_system, 'name', 'contents', 'permissions', 1234)

        """ Try it with all arguments """
        intr.update_file_system('name1', 'contents1', permissions='rwxrw-rw-', location='~/new/place')
        self.assertTrue(intr.state.fs['~/new/place/name1'] == File('~/new/place/name1', 'contents1', 'rwxrw-rw-'))

        """ Try it without location """
        intr.update_file_system('name2', 'contents2', permissions='rwxrw-rw-')
        self.assertTrue(intr.state.fs['~/name2'] == File('~/name2', 'contents2', 'rwxrw-rw-'))

        """ Try it without permissions """
        intr.update_file_system('name3', 'contents3')
        self.assertTrue(intr.state.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))

        """ Update a file already in the file system """
        intr.update_file_system('name3', 'contents4')
        self.assertTrue(intr.state.fs['~/name3'] == File('~/name3', 'contents4', 'rw-rw-rw-'))


    def test_replace(self):
        """ This should mirror test_bpPrimitives.test_replace """
        self.assertRaises(InterpreterError, InterpreterBase().replace, 1234)
        var_list = {'one':['two']}
        intr = InterpreterBase(variables=var_list)
        node = bashparse.parse("echo $one")
        replaced = intr.replace(node)
        self.assertTrue(replaced[0] == bashparse.parse('echo two')[0])

        intr = InterpreterBase(variables={})
        node = bashparse.parse("a=$b")
        replaced = intr.replace(node)
        self.assertTrue(replaced[0] == bashparse.parse('a=')[0])




    def test_build(self):
        intr = Full_Interpreter()               # Need to use full interpreter so echo command is known
        node = bashparse.parse("echo $one")[0]

        self.assertRaises(InterpreterError, intr.build, 1234)
        self.assertRaises(InterpreterError, intr.build, node, 1234)

        intr.build(node)
        self.assertTrue(len(intr.action_stack) == 2)
        self.assertTrue(intr.action_stack[0] == 'Initialize state for command')
        self.assertTrue(intr.action_stack[1] == 'Command node: echo')

        intr.build(node, append = True)
        self.assertTrue(len(intr.action_stack) == 4)
        self.assertTrue(intr.action_stack[0] == 'Initialize state for command')
        self.assertTrue(intr.action_stack[1] == 'Command node: echo')
        self.assertTrue(intr.action_stack[2] == 'Initialize state for command')
        self.assertTrue(intr.action_stack[3] == 'Command node: echo')


    def test_set_variable(self):
        self.assertRaises(InterpreterError, InterpreterBase().set_variable, 1234, 'value')
        self.assertRaises(InterpreterError, InterpreterBase().set_variable, 'name', 1234)

        intr = InterpreterBase()
        intr.set_variable('name1', 'value1')
        intr.set_variable('name2', [ 'value2', 'value3' ])
        self.assertTrue(intr.state.variables['name1'] == [ 'value1' ])
        self.assertTrue(intr.state.variables['name2'] == [ 'value2', 'value3' ])


    def test_stdin(self):
        intr = InterpreterBase()
        self.assertRaises(InterpreterError, intr.stdin, 1234)
        intr.stdin()
        self.assertTrue(intr.state.STDIO.IN == '')
        intr.stdin('something')
        self.assertTrue(intr.state.STDIO.IN == 'something')
        intr.stdin('else')
        self.assertTrue(intr.state.STDIO.IN == 'else')


    def test_stdout(self):
        intr = InterpreterBase()
        self.assertRaises(InterpreterError, intr.stdout, 1234)
        intr.stdout()
        self.assertTrue(intr.state.STDIO.OUT == '')
        intr.stdout('something')
        self.assertTrue(intr.state.STDIO.OUT == 'something')
        intr.stdout('else')
        self.assertTrue(intr.state.STDIO.OUT == 'else')


    def test_inch(self):
        intr = Full_Interpreter()

        self.assertTrue(intr.inch() == False)
        self.assertTrue(intr.state.STDIO.OUT == '')

        node = bashparse.parse('echo hello world')[0]
        intr.build(node)

        self.assertTrue(intr.state.STDIO.OUT == '')
        self.assertTrue(intr.inch())
        self.assertTrue(intr.inch())
        self.assertTrue(intr.state.STDIO.OUT == 'hello world')


    def test_run(self):
        intr = Full_Interpreter()
        self.assertRaises(InterpreterError, intr.run, 1234)

        node1 = bashparse.parse('echo hello world')[0]
        node2 = bashparse.parse('echo this')[0]
        
        """ Verify it works normally """
        intr.run(node1)
        self.assertTrue(intr.state.STDIO.OUT == 'hello world')
        intr.state.STDIO.OUT = ''

        """ Verify it overrides build stack """
        intr.build(node1)
        intr.run(node2)
        self.assertTrue(intr.state.STDIO.OUT == 'this')
        intr.state.STDIO.OUT = ''
        
        """ Verify it works if command is pre-built """
        intr.build(node1)
        intr.run()
        self.assertTrue(intr.state.STDIO.OUT == 'hello world')


    def test_run_command(self):
        """ Test valid command pushed onto stack """
        cmd_node = bashparse.parse('echo this')[0]
        intr = Full_Interpreter()
        intr.run_command(cmd_node.parts[0], cmd_node.parts[1:], cmd_node)

        self.assertTrue(len(intr.action_stack) == 1)
        self.assertTrue(str(intr.action_stack[-1]) == 'Command node: echo')

        """ Test assignment node """
        assign_node = bashparse.parse('a=b')[0]
        intr.run_command(assign_node.parts[0], assign_node.parts[1:], assign_node)
        self.assertTrue(len(intr.action_stack) == 2)
        self.assertTrue(str(intr.action_stack[-1]) == 'Variable Assignment')

        """ Test invalid command push onto stack """
        unknown_node = bashparse.parse('TestingCommand -flg arg ument')[0]
        intr.run_command(unknown_node.parts[0], unknown_node.parts[1:], unknown_node)
        self.assertTrue(len(intr.action_stack) == 3)
        self.assertTrue(str(intr.action_stack[-1]) == 'Unknown command: TestingCommand. Possibly Passing')

        """ Verify command substitution pushing onto the stack """
        intr.action_stack = []
        cmd_sub_node = bashparse.parse('a=$(echo this)')[0]
        intr.run_command(cmd_sub_node.parts[0], cmd_sub_node.parts[1:], cmd_sub_node)
        self.assertTrue(str(intr.action_stack[0]) == 'Resolving Command Substitution in Assignment')
        self.assertTrue(str(intr.action_stack[1]) == 'Variable Assignment')


    def test_set_truth(self):
        intr = InterpreterBase()
        self.assertRaises(InterpreterError, intr.set_truth, 1234, 't')
        self.assertRaises(InterpreterError, intr.set_truth, 'something', 1234)

        intr.set_truth('something', True)
        self.assertTrue(intr.test_truth('something'))


    def test_test_truth(self):
        intr = InterpreterBase()
        self.assertRaises(InterpreterError, intr.test_truth, 1234)

        intr.set_truth('something', True)
        self.assertTrue(intr.test_truth('something'))

        intr.set_truth('something', False)
        self.assertTrue(not intr.test_truth('something'))


    def test_interpreter(self):
        """ Add random edge cases to this section? """
        pass