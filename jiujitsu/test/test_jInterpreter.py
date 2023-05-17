from unittest import TestCase

from jiujitsu import jjInterpreter as Interpreter
from jiujitsu import File, FileSocket
from jiujitsu import Parser, Flag, Arg

import bashparser, os, copy, sys

old_stdout = sys.stdout # backup current stdout

class TestjInterpreter(TestCase):
    def squelch(self):
        sys.stdout = open(os.devnull, "w")
        
    def unsquelch(self):
        sys.stdout = old_stdout # reset old stdout

    def test_args_to_str(self):
        # Test with unescaping the text
        string = r'arg1 arg2 "arg3.1 \t\"arg3.2\"" arg4'
        flags, args = Parser().parse(string)
        expected_string = r'arg1 arg2 "arg3.1 \t\"arg3.2\"" arg4'
        result_string = Interpreter().args_to_str(args, unescape=True)
        self.assertTrue(result_string == expected_string)

        # Test without unescaping the string #
        result_string = Interpreter().args_to_str(args, unescape=False)
        expected_string = 'arg1 arg2 arg3.1 \t"arg3.2" arg4'
        self.assertTrue(result_string == expected_string)
        
        # Verify the default value #
        result_string = Interpreter().args_to_str(args)
        expected_string = 'arg1 arg2 arg3.1 \t"arg3.2" arg4'
        self.assertTrue(result_string == expected_string)

    def test_load(self):
        self.squelch()
        intr = Interpreter()
        intr.do_load('test.sh')
        self.unsquelch()
        # Build correct answers #
        nodes = bashparser.parse('mv /usr/bin/something /usr/bin/else') + bashparser.parse('echo this') + bashparser.parse('cat test.sh | grep grep')
        nodes[1] = bashparser.align(nodes[1], nodes[0].pos[1] + 1)
        nodes[2] = bashparser.align(nodes[2], nodes[1].pos[1] + 1)
        
        #  Verify the nodes properly loaded into Interpreter.prog_nodes #
        self.assertTrue(len(intr.prog_nodes) == len(nodes))
        for i, node in enumerate(nodes):
            self.assertTrue(intr.prog_nodes[i] == nodes[i])

        # Verify nothing happens if not text for filename #
        self.squelch()
        intr.do_load('')
        self.unsquelch()
        for i, node in enumerate(nodes):
            self.assertTrue(intr.prog_nodes[i] == nodes[i])


    def test_next(self):
        intr = Interpreter()

        intr.maintain_history = False
        initial_env_len = len(intr.history_stack)

        # Run the command flat out. No new history should be added #
        intr.prog_nodes = bashparser.parse('echo hello world')
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == 'hello world\n')
        self.assertTrue(initial_env_len == len(intr.history_stack))

        # Verify h flag will create a new history entry #
        intr.prog_nodes = bashparser.parse('echo hello world')
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('-h')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == 'hello world\n')
        self.assertTrue(initial_env_len + 1 == len(intr.history_stack))
        intr.history_stack = intr.history_stack[:-1]

        # Verify i flag will alias to build #
        intr.prog_nodes = bashparser.parse('echo hello world')
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('-i')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == '')
        self.assertTrue(3 == len(intr.env.action_stack))
        intr.history_stack = intr.history_stack[:-1]

        # Verify the e flag will execute in the environment #
        # Actually move a file in the env #
        intr.env.state.update_file_system('test.sh', 'some contents', location='.')
        intr.prog_nodes = bashparser.parse('cp ./test.sh ./test2.sh')
        intr.env.action_stack = []
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('-e')
        self.unsquelch()

        # Verify the move file exists in the env #
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' in files)

        # Delete the file in the env #
        intr.prog_nodes = bashparser.parse('rm ./test2.sh')
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('-e')
        self.unsquelch()
        intr.history_stack = intr.history_stack[:-2]

        # Verify maintain_history = True will add an entry into the history #
        intr.maintain_history = True
        intr.prog_nodes = bashparser.parse('echo hello world')
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('')
        self.unsquelch()
        self.assertTrue(intr.env.get_screen() == 'hello world\n')
        self.assertTrue(initial_env_len == len(intr.history_stack))


    def test_undo(self):
        # Verify undo works in the init case #
        intr = Interpreter(config_file='./judo_config')
        intr.env.state.STDIO.IN = "something random"
        self.squelch()
        intr.do_undo('')
        self.unsquelch()
        intr2 = Interpreter(config_file='./judo_config')
        self.assertTrue(intr.env == intr2.env)
        self.assertTrue(intr.index == intr2.index)
        self.assertTrue(len(intr.history_stack) == len(intr2.history_stack))
        for i, el in enumerate(intr.history_stack):
            self.assertTrue(intr.history_stack[i] == intr2.history_stack[i])
        

        # Verify undo works with more than 1 entry #
        intr.prog_nodes = bashparser.parse('echo hello world')
        intr.index = 0
        intr.env.state.screen = ''
        self.squelch()
        intr.do_next('')
        self.unsquelch()

        intr.prog_nodes = bashparser.parse('echo hello world')
        intr.index = 0
        self.squelch()
        intr.do_next('')
        self.unsquelch()

        self.assertTrue(intr.env.get_screen() == 'hello world\nhello world\n')
        self.assertTrue(3 == len(intr.history_stack))

        self.squelch()
        intr.do_undo('')
        self.unsquelch()
        self.assertTrue(intr.env.get_screen() == 'hello world\n')
        self.assertTrue(2 == len(intr.history_stack))


    def test_skip(self):
        intr = Interpreter()
        self.squelch()
        intr.do_skip('')
        self.unsquelch()
        self.assertTrue(intr.index == 1)


    def test_save(self):
        intr = Interpreter()
        self.squelch()
        intr.do_save('')
        self.unsquelch()
        self.assertTrue(len(intr.history_stack) == 1)   # Shouldn't save 

        self.squelch()
        intr.do_save('some name')
        self.unsquelch()
        self.assertTrue(intr.history_stack[1].name == 'some name')
        self.assertTrue(intr.history_stack[1].action == 'User Save')

    def test_inch(self):
        intr = Interpreter()
        self.squelch()
        intr.do_build("echo this")
        for el in intr.env.action_stack:
            print(el)
        intr.do_inch('')
        intr.do_inch('')
        self.assertTrue(intr.env.state.STDIO.OUT == 'this')
        intr.do_inch('')
        self.unsquelch()
        self.assertTrue(len(intr.env.action_stack) == 0)

        # Test that exiting the interpreter with inch works just fine
        intr = Interpreter()
        self.squelch()
        intr.do_load('test.sh')
        intr.do_next('')
        intr.do_next('')
        intr.do_next("-i")
        self.unsquelch()
        self.assertTrue(intr.index == 2)
        self.squelch()
        intr.do_inch('')
        intr.do_inch('-e')
        intr.do_inch('')
        intr.do_inch('-e')
        intr.do_inch('')
        self.unsquelch()
        self.assertTrue(intr.env.get_screen() == 'this\ncat test.sh | grep grep\n\n')

    def test_run(self):
        intr = Interpreter()
        self.squelch()
        intr.do_load('test.sh')
        self.unsquelch()

        # Build correct answers #
        nodes = bashparser.parse('mv /usr/bin/something /usr/bin/else') + bashparser.parse('echo this') + bashparser.parse('cat test.sh | grep grep')
        nodes[1] = bashparser.align(nodes[1], nodes[0].pos[1] + 1)
        nodes[2] = bashparser.align(nodes[2], nodes[1].pos[1] + 1)
        
        #  Verify the nodes properly loaded into Interpreter.prog_nodes #
        self.assertTrue(len(intr.prog_nodes) == len(nodes))
        for i, node in enumerate(nodes):
            self.assertTrue(intr.prog_nodes[i] == nodes[i])

    def test_next(self):
        intr = Interpreter()

        intr.maintain_history = False
        initial_env_len = len(intr.history_stack)

        # Run the command flat out. No new history should be added #
        intr.env.state.screen = ''
        self.squelch()
        intr.do_run('echo hello world')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == 'hello world\n')
        self.assertTrue(initial_env_len == len(intr.history_stack))

        # Verify h flag will create a new history entry #
        intr.env.state.screen = ''
        self.squelch()
        intr.do_run('-h echo hello world')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == 'hello world\n')
        self.assertTrue(initial_env_len + 1 == len(intr.history_stack))
        intr.history_stack = intr.history_stack[:-1]

        # Verify i flag will alias to build #
        intr.env.state.screen = ''
        self.squelch()
        intr.do_run('-i echo hello world')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == '')
        self.assertTrue(len(intr.env.action_stack) == 3)
        intr.history_stack = intr.history_stack[:-1]

        # Verify the e flag will execute in the environment #
        # Actually move a file in the env #
        intr.env.state.update_file_system('test.sh', 'some contents', location='.')
        intr.env.state.screen = ''
        self.squelch()
        intr.do_run('-e cp ./test.sh ./test2.sh')
        self.unsquelch()

        # Verify the move file exists in the env #
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' in files)

        # Delete the file in the env #
        self.squelch()
        intr.do_run('-e rm ./test2.sh')
        self.unsquelch()
        intr.history_stack = intr.history_stack[:-2]

        # Verify maintain_history = True will add an entry into the history #
        intr.env.state.screen = ''
        intr.maintain_history = True
        self.squelch()
        intr.do_run('echo hello world')
        self.unsquelch()
        self.assertTrue(intr.env.state.get_screen() == 'hello world\n')
        self.assertTrue(initial_env_len == len(intr.history_stack))

    def test_build(self):
        intr = Interpreter()
        self.squelch()
        intr.do_build('echo this')
        self.unsquelch()
        
        self.assertTrue(str(intr.env.action_stack[0]) == 'Initialize state for command')
        self.assertTrue(str(intr.env.action_stack[1]) == 'Command node: echo')
        self.assertTrue(str(intr.env.action_stack[2]) == 'Exit Node Cleanup')
        self.assertTrue(len(intr.env.action_stack) == 3)

        # Verify that append works #
        self.squelch()
        intr.do_build('-a echo this')
        self.unsquelch()
        for i in range(0, len(intr.env.action_stack)-1, 3):
            self.assertTrue(str(intr.env.action_stack[i]) == 'Initialize state for command')
            self.assertTrue(str(intr.env.action_stack[i+1]) == 'Command node: echo')
            self.assertTrue(str(intr.env.action_stack[i+2]) == 'Exit Node Cleanup')

        self.assertTrue(len(intr.env.action_stack) == 6)

    def test_syscall(self):
        self.squelch()
        Interpreter().do_shell('cp test.sh test2.sh')
        self.unsquelch()
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' in files)
        self.squelch()
        Interpreter().do_shell('rm test2.sh')
        self.unsquelch()
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' not in files)

    def test_dir(self):
        intr = Interpreter()
        self.squelch()
        intr.do_dir('one two')
        self.unsquelch()
        self.assertTrue(intr.env.state.working_dir == '~')

        self.squelch()
        intr.do_dir('~/one')
        self.unsquelch()
        self.assertTrue(intr.env.state.working_dir == '~/one')

    def test_stdin(self):
        intr = Interpreter()
        self.squelch()
        intr.do_stdin('some text')
        self.unsquelch()
        self.assertTrue(intr.env.state.STDIO.IN == 'some text')

    def test_stdout(self):
        intr = Interpreter()
        self.squelch()
        intr.do_stdout('some text')
        self.unsquelch()
        self.assertTrue(intr.env.state.STDIO.OUT == 'some text')


    def test_var(self):
        intr = Interpreter()
        self.squelch()
        intr.do_var('name1:value1 name2 : value2')
        self.unsquelch()
        self.assertTrue(intr.env.state.variables['name1'] == ['value1'])
        self.assertTrue(intr.env.state.variables['name2'] == ['value2'])

        self.squelch()
        intr.do_var('-p name1 : value1.5 name2:value2.5')
        self.unsquelch()
        self.assertTrue(intr.env.state.variables['name1'] == ['value1.5'])
        self.assertTrue(intr.env.state.variables['name2'] == ['value2.5'])

    def test_fs(self):
        # Verify that it works for 1 #
        intr = Interpreter()
        self.squelch()
        intr.do_fs('name1:contents1:rwxrw-rw-')
        self.unsquelch()
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File(name='~/name1', contents='contents1', permissions='rwxrw-rw-'))

        # Verify that it works for multiple #
        intr = Interpreter()
        self.squelch()
        intr.do_fs('name1:contents1:rw-rw-rw- name2:contents2:rw-rw-rw- \
                name3 : contents3 : rw-rw-rw-')
        self.unsquelch()
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File('~/name1', 'contents1', 'rw-rw-rw-'))
        self.assertTrue('~/name2' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name2'] == File('~/name2', 'contents2', 'rw-rw-rw-'))
        self.assertTrue('~/name3' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))

        # Verify that it adds permisions for 1 #
        intr = Interpreter()
        self.squelch()
        intr.do_fs('name1:contents1')
        self.unsquelch()
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File('~/name1', 'contents1', 'rw-rw-rw-'))

        # Verify it adds permissions for multiple #
        intr = Interpreter()
        self.squelch()
        intr.do_fs('name1:contents1   name2 : contents2 name3: contents3')
        self.unsquelch()
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File('~/name1', 'contents1', 'rw-rw-rw-'))
        self.assertTrue('~/name2' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name2'] == File('~/name2', 'contents2', 'rw-rw-rw-'))
        self.assertTrue('~/name3' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))

    def test_history(self):
        intr = Interpreter()

        self.squelch()
        intr.do_history('on')
        self.unsquelch()
        self.assertTrue(intr.maintain_history == True)

        self.squelch()
        intr.do_history('off')
        self.unsquelch()
        self.assertTrue(intr.maintain_history == False)

        self.squelch()
        intr.do_history('toggle')
        self.unsquelch()
        self.assertTrue(intr.maintain_history == True)

    def test_alias(self):
        intr = Interpreter()
        self.squelch()
        intr.do_alias('t run echo this')
        self.unsquelch()
        expected_json = {
            't':'run echo this'
        }
        self.assertTrue(expected_json == intr.alias_table)

    def test_truth(self):
        intr = Interpreter()
        self.squelch()
        intr.do_truth('this:true that:false one:t two:f two')
        self.unsquelch()
        self.assertTrue(intr.env.state.truths == {})

        self.squelch()
        intr.do_truth('this:true that:false one:t two:f')
        self.unsquelch()
        expected_json = {
            'this':True,
            'that':False,
            'one':True, 
            'two':False,
        }
        self.assertTrue(expected_json == intr.env.state.truths)

    
    def test_env(self):
        intr = Interpreter()
        self.squelch()
        intr.do_alias('this:that')
        intr.do_stdin('something')
        intr.do_stdout('else')
        intr.do_dir('~/here')
        intr.do_var('one:two three:four')
        intr.do_fs('this:contents:rw-rw-rwx')
        intr.do_truth('this:true that:false')
        intr.do_env('-e testing_config')
        intr2 = Interpreter()
        intr2.do_env('-a testing_config')
        self.unsquelch()
        self.assertTrue(intr2.env == intr.env)
        self.squelch()
        intr.do_run('-e rm testing_config')
        self.unsquelch()
