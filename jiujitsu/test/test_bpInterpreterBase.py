from unittest import TestCase

from jiujitsu import InterpreterBase, InterpreterError
from jiujitsu import FullInterpreter as Full_Interpreter
from jiujitsu import State
from jiujitsu import File, FileSocket

import bashparser

class TestBpInterpreterBase(TestCase):
    def test_init(self):
        # Verify all the objects are created correctly with no arguments #
        intr = InterpreterBase()
        state = State()
        self.assertTrue(intr.state == state)
        self.assertTrue(intr.action_stack == [])
        self.assertTrue(intr.execute == True)

        # Verify the passed in arguments work well #
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
        # Only need to verify execute wraps properly. state is checked in bpPrimatives #
        intr = InterpreterBase(execute = False)
        self.assertTrue(intr.json()['execute'] == 'f')
        intr = InterpreterBase(execute = True)
        self.assertTrue(intr.json()['execute'] == 't')


    def test_working_dir(self):
        intr = InterpreterBase()
        self.assertTrue(intr.working_dir() == '~')
        self.assertTrue(intr.working_dir('~/some/where') == '~/some/where')


    def test_update_file_system(self):
        # This should mirror test_bpPrimitives.test_update_file_system #
        intr = InterpreterBase()

        self.assertRaises(InterpreterError, intr.update_file_system, 1234, 'contents')
        self.assertRaises(InterpreterError, intr.update_file_system, 'name', 1234)
        self.assertRaises(InterpreterError, intr.update_file_system, 'name', 'contents', 1234)
        self.assertRaises(InterpreterError, intr.update_file_system, 'name', 'contents', 'permissions', 1234)

        # Try it with all arguments #
        intr.update_file_system('name1', 'contents1', permissions='rwxrw-rw-', location='~/new/place')
        self.assertTrue(intr.state.fs['~/new/place/name1'] == File('~/new/place/name1', 'contents1', 'rwxrw-rw-'))

        # Try it without location #
        intr.update_file_system('name2', 'contents2', permissions='rwxrw-rw-')
        self.assertTrue(intr.state.fs['~/name2'] == File('~/name2', 'contents2', 'rwxrw-rw-'))

        # Try it without permissions #
        intr.update_file_system('name3', 'contents3')
        self.assertTrue(intr.state.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))

        # Update a file already in the file system #
        intr.update_file_system('name3', 'contents4')
        self.assertTrue(intr.state.fs['~/name3'] == File('~/name3', 'contents4', 'rw-rw-rw-'))


    def test_replace(self):
        # This should mirror test_bpPrimitives.test_replace #
        self.assertRaises(InterpreterError, InterpreterBase().replace, 1234)
        var_list = {'one':['two']}
        intr = InterpreterBase(variables=var_list)
        node = bashparser.parse("echo $one")
        replaced = intr.replace(node)
        self.assertTrue(replaced[0] == bashparser.parse('echo two')[0])

        intr = InterpreterBase(variables={})
        node = bashparser.parse("a=$b")
        replaced = intr.replace(node)
        self.assertTrue(replaced[0] == bashparser.parse('a=')[0])




    def test_build(self):
        intr = Full_Interpreter()               # Need to use full interpreter so echo command is known
        node = bashparser.parse("echo $one")[0]

        self.assertRaises(InterpreterError, intr.build, 1234)
        self.assertRaises(InterpreterError, intr.build, node, 1234)

        intr.build(node)
        self.assertTrue(len(intr.action_stack) == 3)
        self.assertTrue(intr.action_stack[0] == 'Initialize state for command')
        self.assertTrue(intr.action_stack[1] == 'Command node: echo')
        self.assertTrue(intr.action_stack[2] == 'Exit Node Cleanup')

        intr.build(node, append = True)
        self.assertTrue(len(intr.action_stack) == 6)
        self.assertTrue(intr.action_stack[0] == 'Initialize state for command')
        self.assertTrue(intr.action_stack[1] == 'Command node: echo')
        self.assertTrue(intr.action_stack[2] == 'Exit Node Cleanup')
        self.assertTrue(intr.action_stack[3] == 'Initialize state for command')
        self.assertTrue(intr.action_stack[4] == 'Command node: echo')
        self.assertTrue(intr.action_stack[5] == 'Exit Node Cleanup')


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

        node = bashparser.parse('echo hello world')[0]
        intr.build(node)

        self.assertTrue(intr.state.STDIO.OUT == '')
        self.assertTrue(intr.inch())
        self.assertTrue(intr.inch())
        self.assertTrue(intr.state.STDIO.OUT == 'hello world')


    def test_run(self):
        intr = Full_Interpreter()
        self.assertRaises(InterpreterError, intr.run, 1234)

        node1 = bashparser.parse('echo hello world')[0]
        node2 = bashparser.parse('echo this')[0]
        
        # Verify it works normally #
        intr.run(node1)
        self.assertTrue(intr.get_screen() == 'hello world\n')
        intr.state.STDIO.OUT = ''

        # Verify it overrides build stack #
        intr.build(node1)
        intr.run(node2)
        self.assertTrue(intr.get_screen() == 'hello world\nthis\n')
        intr.state.STDIO.OUT = ''
        
        # Verify it works if command is pre-built #
        intr.state.screen = ""
        intr.build(node1)
        intr.run()
        self.assertTrue(intr.get_screen() == 'hello world\n')


    def test_run_command(self):
        # Test valid command pushed onto stack #
        cmd_node = bashparser.parse('echo this')[0]
        intr = Full_Interpreter()
        intr.run_command(cmd_node.parts[0], cmd_node.parts[1:], cmd_node)

        self.assertTrue(len(intr.action_stack) == 1)
        self.assertTrue(str(intr.action_stack[-1]) == 'Command node: echo')

        # Test assignment node #
        assign_node = bashparser.parse('a=b')[0]
        intr.run_command(assign_node.parts[0], assign_node.parts[1:], assign_node)
        self.assertTrue(len(intr.action_stack) == 3)
        self.assertTrue(str(intr.action_stack[-1]) == 'Variable Assignment')

        # Test invalid command push onto stack #
        unknown_node = bashparser.parse('TestingCommand -flg arg ument')[0]
        intr.run_command(unknown_node.parts[0], unknown_node.parts[1:], unknown_node)
        self.assertTrue(len(intr.action_stack) == 4)
        self.assertTrue(str(intr.action_stack[-1]) == 'Command node: TestingCommand')

        # Verify command substitution pushing onto the stack #
        intr.action_stack = []
        cmd_sub_node = bashparser.parse('a=$(echo this)')[0]
        intr.run_command(cmd_sub_node.parts[0], cmd_sub_node.parts[1:], cmd_sub_node)
        self.assertTrue(str(intr.action_stack[0]) == 'Entering Assignment Node: a=$(echo this)')
        self.assertTrue(str(intr.action_stack[1]) == 'Enter Command Substitution Env: a=$(echo this)')
        self.assertTrue(str(intr.action_stack[2]) == 'Exiting Command Substitution Env: a=$(echo this)')
        self.assertTrue(str(intr.action_stack[3]) == 'Variable Assignment')


    def test_set_truth(self):
        intr = InterpreterBase()
        self.assertRaises(InterpreterError, intr.set_truth, 1234, 't')
        self.assertRaises(InterpreterError, intr.set_truth, 'something', 1234)

        intr.set_truth('something', True)
        self.assertTrue(intr.test_truth('something'))


    def test_test_truth(self):
        intr = InterpreterBase()

        intr.set_truth('something', True)
        self.assertTrue(intr.test_truth('something'))

        intr.set_truth('something', False)
        self.assertTrue(not intr.test_truth('something'))


    def test_command_substitution(self):
        # Verify the replacement works
        node = bashparser.parse("f=$(cd $b)")[0]
        intr = Full_Interpreter()
        intr.run(node)
        self.assertTrue(intr.state.variables == {'f':['']})

        # Verify the file system changes properly with cp
        intr = Full_Interpreter()
        node = bashparser.parse("$(cp this that)")[0]
        intr.run(node)
        expected_intr = Full_Interpreter()
        expected_intr.run(bashparser.parse("cp this that")[0])
        self.assertTrue(intr.state.fs == expected_intr.state.fs)

        # Verify the file system changes properly with mv
        intr = Full_Interpreter()
        node = bashparser.parse("$(mv over rainbow)")[0]
        intr.run(node)
        expected_intr = Full_Interpreter()
        expected_intr.run(bashparser.parse("mv over rainbow")[0])
        self.assertTrue(intr.state.fs == expected_intr.state.fs)

        # Verify the stdout is replaced properly with echo
        intr = Full_Interpreter()
        node = bashparser.parse("echo $(echo this)")[0]
        intr.run(node)
        self.assertTrue(intr.get_screen() == 'this\n')


    def test_interpreter(self):
        # Add random edge cases to this section #

        # Verify the variable assignment only happens when inched through. 
            # This was a bug that happened #
        bash_node = bashparser.parse('echo a; b=3; echo $b; b=4; echo $b')[0]
        intr = Full_Interpreter()
        expected_state = State()
        intr.build(bash_node)
        self.assertTrue(expected_state == intr.state)
        intr.inch() # init state for command
        self.assertTrue(expected_state == intr.state)
        intr.inch() # list node entry
        intr.inch() # Resetting stdout for a new command
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # echo command
        expected_state.STDOUT('a')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Transfer character
        intr.inch() # Resetting stdout for a new command
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Entering assignment node
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Variable assignment
        expected_state.set_variable('b', '3')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Transfer character
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Resetting stdout for a new command
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # echo command
        expected_state.STDOUT('3')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Transfer character
        intr.inch() # Resetting stdout for a new command
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Entering assignment node
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Variable assignment
        expected_state.set_variable('b', '4')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Transfer character
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # Resetting stdout for a new command
        expected_state.STDOUT('')
        self.assertTrue(expected_state == intr.state)
        intr.inch() # echo command
        expected_state.STDOUT('4')
        self.assertTrue(expected_state == intr.state)


    def test_functions(self):
        code = "PrintStuff(){\n \
                    echo this $1\n \
                }\n \
                PrintStuff wordsIn"

        nodes = bashparser.parse(code)

        intr = Full_Interpreter()
        intr.run(nodes[0])
        intr.build(nodes[1])
        intr.inch() # init state for command
        intr.inch() # actual function node
        # Now the function should be replaced
        self.assertTrue(str(intr.action_stack[0] == 'Enter the function scope'))
        self.assertTrue(str(intr.action_stack[0] == 'Command node: echo'))
        self.assertTrue(str(intr.action_stack[0] == 'Exit the function scope'))
        intr.inch()
        intr.inch()
        self.assertTrue(intr.stdout() == 'this wordsIn')


    def test_file_redirects(self):
        code = '( echo "text for the file" ) > ~/testing'
        nodes = bashparser.parse(code)
        intr = Full_Interpreter()
        intr.run(nodes[0])
        self.assertTrue('~/testing' in intr.state.fs)


    def test_variable_scoping(self):
        # just regular scoping
        code = 'a="upper scope"; b=$(a="lower scope"; echo $a)'
        nodes = bashparser.parse(code)
        intr = Full_Interpreter()
        intr.run(nodes[0])
        self.assertTrue(intr.state.variables == {'a':['upper scope'], 'b':['lower scope']})

        # Variable scoping and function scoping in one go
        code = """Print1() {
                    echo $a
                  }
                  a="upper scope"; b=$(a="lower scope"; Print1)"""
        nodes = bashparser.parse(code)
        intr = Full_Interpreter()
        intr.run(nodes[0])
        intr.run(nodes[1])
        self.assertTrue(intr.state.variables == {'a':['upper scope'], 'b':['lower scope ']})


    def test_substringing(self):
        code = 'a="this node"; b=${a:0:4}'
        nodes = bashparser.parse(code)
        intr = Full_Interpreter()
        intr.run(nodes[0])
        self.assertTrue(intr.state.variables == {'a':['this node'], 'b':['this']})
        
    def test_array_indexing(self):
        code = 'a="not an array"; b=${a[2]}'
        nodes = bashparser.parse(code)
        intr = Full_Interpreter()
        intr.run(nodes[0])
        self.assertTrue(intr.state.variables == {'a':['not an array'], 'b':['']})

    def test_quoted_command_substitution_replacement(self):
        code = """Print1() {
                    echo $a
                  }
                  a="upper scope"; b=\"$(a="lower scope"; Print1)\""""
        nodes = bashparser.parse(code)
        intr = Full_Interpreter()
        intr.run(nodes[0])
        intr.run(nodes[1])
        self.assertTrue(intr.state.variables == {'a':['upper scope'], 'b':['lower scope ']})



    # This test requires user interaction so its been removed
    # Just verify it every one in  while
    # Could also consider adding functionality to execute automatically
    # def test_commands_in_if_statements(self):
    #     code = 'if echo "this"; then echo success; else echo failed; fi'
    #     nodes = bashparser.parse(code)
    #     intr = Full_Interpreter()
    #     intr.run(nodes[0])
    #     self.assertTrue(intr.state.get_screen() == 'success\n')
        


