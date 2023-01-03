from unittest import TestCase
from jInterpreter import Interpreter, InterpreterExitStatus
from jLexer import Lexer
from jToken import Token, TokenType
from jNode import Flag, Arg
from bpFileSystem import File, FileSocket
import bashparse, os, copy

class TestjInterpreter(TestCase):

    def test_args_to_str(self):
        """ Test with unescaping the text """
        string = r'cmd arg1 arg2 "arg3.1 \t\"arg3.2\"" arg4'
        tokens = Lexer(string).get_all_tokens()[1:-1]   # Remove cmd and EOF
        expected_string = r'arg1 arg2 "arg3.1 \t\"arg3.2\"" arg4'
        result_string = Interpreter().args_to_str(tokens, unescape=True)
        self.assertTrue(result_string == expected_string)

        """ Test without unescaping the string """
        result_string = Interpreter().args_to_str(tokens, unescape=False)
        expected_string = 'arg1 arg2 arg3.1 \t"arg3.2" arg4'
        self.assertTrue(result_string == expected_string)
        
        """ Verify the default value """
        result_string = Interpreter().args_to_str(tokens)
        expected_string = 'arg1 arg2 arg3.1 \t"arg3.2" arg4'
        self.assertTrue(result_string == expected_string)


    def test_load(self):
        intr = Interpreter()
        arg = Token(TokenType.ARG, 'test.sh')
        intr.load([], arg)
        
        """ Build correct answers """
        nodes = bashparse.parse('mv /usr/bin/something /usr/bin/else') + bashparse.parse('echo this')
        nodes[1] = bashparse.align(nodes[1], nodes[0].pos[1] + 1)
        
        """  Verify the nodes properly loaded into Interpreter.prog_nodes """
        self.assertTrue(len(intr.prog_nodes) == len(nodes))
        for i, node in enumerate(nodes):
            self.assertTrue(intr.prog_nodes[i] == nodes[i])


    def test_next(self):
        intr = Interpreter()
        args = [ Token(TokenType.ARG, 'echo'), Token(TokenType.ARG, 'hello'), Token(TokenType.ARG, 'world') ]
        
        intr.maintain_history = False
        initial_env_len = len(intr.history_stack)

        """ Run the command flat out. No new history should be added """
        intr.prog_nodes = bashparse.parse('echo hello world')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([], args)
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(initial_env_len == len(intr.history_stack))

        """ Verify h flag will create a new history entry """
        intr.prog_nodes = bashparse.parse('echo hello world')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([Flag('h')], args)
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(initial_env_len + 1 == len(intr.history_stack))
        intr.history_stack = intr.history_stack[:-1]

        """ Verify i flag will alias to build """
        intr.prog_nodes = bashparse.parse('echo hello world')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([Flag('i')], args)
        self.assertTrue(intr.env.state.STDIO.OUT == '')
        self.assertTrue(1 == len(intr.env.action_stack))
        intr.history_stack = intr.history_stack[:-1]

        """ Verify the e flag will execute in the environment """
        """ Actually move a file in the env """
        intr.env.state.update_file_system('test.sh', 'some contents', location='.')
        intr.prog_nodes = bashparse.parse('cp ./test.sh ./test2.sh')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([Flag('e')], args)

        """ Verify the move file exists in the env """
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' in files)

        """ Delete the file in the env """
        intr.prog_nodes = bashparse.parse('rm ./test2.sh')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([Flag('e')], args)
        intr.history_stack = intr.history_stack[:-2]

        """ Verify maintain_history = True will add an entry into the history """
        intr.maintain_history = True
        intr.prog_nodes = bashparse.parse('echo hello world')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([], args)
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(initial_env_len == len(intr.history_stack))


    def test_undo(self):
        """ Verify undo works in the init case """
        intr = Interpreter()
        args = [ Token(TokenType.ARG, 'echo'), Token(TokenType.ARG, 'hello'), Token(TokenType.ARG, 'world') ]
        intr.env.state.STDIO.IN = "something random"
        intr.undo([])
        intr2 = Interpreter()
        self.assertTrue(intr.env == intr2.env)
        self.assertTrue(intr.index == intr2.index)
        self.assertTrue(len(intr.history_stack) == len(intr2.history_stack))
        for i, el in enumerate(intr.history_stack):
            self.assertTrue(intr.history_stack[i] == intr2.history_stack[i])
        

        """ Verify undo works with more than 1 entry """
        intr.prog_nodes = bashparse.parse('echo hello world')
        intr.index = 0
        intr.env.state.STDIO.OUT = ''
        intr.next([], args)

        intr.prog_nodes = bashparse.parse('echo hello world')
        intr.index = 0
        intr.next([], args)

        self.assertTrue(intr.env.state.STDIO.OUT == 'hello worldhello world')
        self.assertTrue(3 == len(intr.history_stack))

        intr.undo([])
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(2 == len(intr.history_stack))



    def test_skip(self):
        intr = Interpreter()
        intr.skip([])
        self.assertTrue(intr.index == 1)


    def test_save(self):
        intr = Interpreter()
        res = intr.save([])
        self.assertTrue(res.status == 1)

        res = intr.save([], Arg("some name"))
        self.assertTrue(res == InterpreterExitStatus("SUCCESS"))
        self.assertTrue(intr.history_stack[1].name == 'some name')
        self.assertTrue(intr.history_stack[1].action == 'User Save')


    def test_inch(self):
        intr = Interpreter()
        res = intr.inch([])
        self.assertTrue(res.status == 1)

        intr.build([], Arg("echo this"))
        res = intr.inch([])
        self.assertTrue(res == InterpreterExitStatus("SUCCESS"))
        self.assertTrue(intr.env.state.STDIO.OUT == 'this')
        self.assertTrue(len(intr.env.action_stack) == 0)


    def test_run(self):
        intr = Interpreter()
        arg = Token(TokenType.ARG, 'test.sh')
        intr.load([], arg)
        
        """ Build correct answers """
        nodes = bashparse.parse('mv /usr/bin/something /usr/bin/else') + bashparse.parse('echo this')
        nodes[1] = bashparse.align(nodes[1], nodes[0].pos[1] + 1)
        
        """  Verify the nodes properly loaded into Interpreter.prog_nodes """
        self.assertTrue(len(intr.prog_nodes) == len(nodes))
        for i, node in enumerate(nodes):
            self.assertTrue(intr.prog_nodes[i] == nodes[i])


    def test_next(self):
        intr = Interpreter()
        args = [ Token(TokenType.ARG, 'echo'), Token(TokenType.ARG, 'hello'), Token(TokenType.ARG, 'world') ]
        
        intr.maintain_history = False
        initial_env_len = len(intr.history_stack)

        """ Run the command flat out. No new history should be added """
        intr.env.state.STDIO.OUT = ''
        intr.run([], *args)
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(initial_env_len == len(intr.history_stack))

        """ Verify h flag will create a new history entry """
        intr.env.state.STDIO.OUT = ''
        intr.run([Flag('h')], *args)
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(initial_env_len + 1 == len(intr.history_stack))
        intr.history_stack = intr.history_stack[:-1]

        """ Verify i flag will alias to build """
        intr.env.state.STDIO.OUT = ''
        intr.run([Flag('i')], *args)
        self.assertTrue(intr.env.state.STDIO.OUT == '')
        self.assertTrue(1 == len(intr.env.action_stack))
        intr.history_stack = intr.history_stack[:-1]

        """ Verify the e flag will execute in the environment """
        """ Actually move a file in the env """
        args = [ Token(TokenType.ARG, 'cp'), Token(TokenType.ARG, './test.sh'), Token(TokenType.ARG, './test2.sh') ]
        intr.env.state.update_file_system('test.sh', 'some contents', location='.')
        intr.env.state.STDIO.OUT = ''
        intr.run([Flag('e')], *args)

        """ Verify the move file exists in the env """
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' in files)

        """ Delete the file in the env """
        intr.env.state.STDIO.OUT = ''
        args = [ Token(TokenType.ARG, 'rm'), Token(TokenType.ARG, './test2.sh') ]
        intr.run([Flag('e')], *args)
        intr.history_stack = intr.history_stack[:-2]

        """ Verify maintain_history = True will add an entry into the history """
        intr.maintain_history = True
        args = [ Token(TokenType.ARG, 'echo'), Token(TokenType.ARG, 'hello'), Token(TokenType.ARG, 'world') ]
        intr.env.state.STDIO.OUT = ''
        intr.run([], *args)
        self.assertTrue(intr.env.state.STDIO.OUT == 'hello world')
        self.assertTrue(initial_env_len == len(intr.history_stack))


    def test_build(self):
        intr = Interpreter()
        res = intr.build([])

        self.assertTrue(res.status == 1)

        intr.build([], Arg('echo this'))
        for action in intr.env.action_stack:
            self.assertTrue(str(action) == 'Command node: echo')
        self.assertTrue(len(intr.env.action_stack) == 1)

        """ Verify that append works """
        intr.build([Flag('a')], Arg('echo this'))
        for action in intr.env.action_stack:
            self.assertTrue(str(action) == 'Command node: echo')
        self.assertTrue(len(intr.env.action_stack) == 2)


    def test_syscall(self):
        res = Interpreter().syscall(1234)
        self.assertTrue(res.status == 1)

        Interpreter().syscall('cp test.sh test2.sh')
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' in files)
        Interpreter().syscall('rm test2.sh')
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.assertTrue('test2.sh' not in files)


    def test_dir(self):
        intr = Interpreter()
        res = intr.dir([], Arg('one'), Arg('two'))
        self.assertTrue(res.status == 1)
        self.assertTrue(intr.env.state.working_dir == '~')

        res = intr.dir([], Arg('~/one'))
        self.assertTrue(res.status == 0)
        self.assertTrue(intr.env.state.working_dir == '~/one')


    def test_stdin(self):
        intr = Interpreter()
        res = intr.stdin([], Arg('some text'))
        self.assertTrue(res.status == 0)
        self.assertTrue(intr.env.state.STDIO.IN == 'some text')


    def test_stdout(self):
        intr = Interpreter()
        res = intr.stdout([], Arg('some text'))
        self.assertTrue(res.status == 0)
        self.assertTrue(intr.env.state.STDIO.OUT == 'some text')


    def test_var(self):
        intr = Interpreter()
        res = intr.var([], Arg('name1'), Arg(':'), Arg('value1'), Arg('name2'), Arg(':'), Arg('value2'))
        self.assertTrue(res.status == 0)
        self.assertTrue(intr.env.state.variables['name1'] == ['value1'])
        self.assertTrue(intr.env.state.variables['name2'] == ['value2'])

        res = intr.var([Flag('p')], Arg('name1'), Arg(':'), Arg('value1'), Arg('name2'), Arg(':'), Arg('value2'))
        self.assertTrue(res.status == 0)
        self.assertTrue(res.print_out == True)


    def test_fs(self):
        """ Verify that it works for 1 """
        intr = Interpreter()
        res = intr.fs([], Arg('name1'), Arg(':'), Arg('contents1'), Arg(':'), Arg('rwxrw-rw-'))
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File(name='~/name1', contents='contents1', permissions='rwxrw-rw-'))

        """ Verify that it works for multiple """
        intr = Interpreter()
        res = intr.fs([], Arg('name1'), Arg(':'), Arg('contents1'), Arg(':'), Arg('rw-rw-rw-'), 
            Arg('name2'), Arg(':'), Arg('contents2'), Arg(':'), Arg('rw-rw-rw-'), 
            Arg('name3'), Arg(':'), Arg('contents3'), Arg(':'), Arg('rw-rw-rw-'))
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File('~/name1', 'contents1', 'rw-rw-rw-'))
        self.assertTrue('~/name2' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name2'] == File('~/name2', 'contents2', 'rw-rw-rw-'))
        self.assertTrue('~/name3' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))

        """ Verify that it adds permisions for 1 """
        intr = Interpreter()
        res = intr.fs([], Arg('name1'), Arg(':'), Arg('contents1'))
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File('~/name1', 'contents1', 'rw-rw-rw-'))

        """ Verify it adds permissions for multiple """
        intr = Interpreter()
        res = intr.fs([], Arg('name1'), Arg(':'), Arg('contents1'), 
            Arg('name2'), Arg(':'), Arg('contents2'), 
            Arg('name3'), Arg(':'), Arg('contents3'))
        self.assertTrue('~/name1' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name1'] == File('~/name1', 'contents1', 'rw-rw-rw-'))
        self.assertTrue('~/name2' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name2'] == File('~/name2', 'contents2', 'rw-rw-rw-'))
        self.assertTrue('~/name3' in intr.env.state.fs)
        self.assertTrue(intr.env.state.fs['~/name3'] == File('~/name3', 'contents3', 'rw-rw-rw-'))


    def test_json(self):
        """ Test failure """
        res = Interpreter().json([])
        self.assertTrue(res.status == 1)
        
        res = Interpreter().json([], Arg('testing.json'))
        self.assertTrue(res.status == 2)

        """ Test export """
        intr = Interpreter()
        intr.fs([], Arg("name1"), Arg(":"), Arg("value1"))
        res = intr.json([Flag('e')], Arg('testing_exclusive.json'))
        self.assertTrue(open('testing_exclusive.json').read() == open('testing_exclusive_truth.json').read())
        tmp = Interpreter()
        tmp.syscall('rm testing_exclusive.json')


        """ Test import """
        intr = Interpreter()
        intr.json([Flag('i')], Arg('testing_exclusive_truth.json'))
        intr2 = Interpreter()
        intr2.fs([], Arg("name1"), Arg(":"), Arg("value1"))
        self.assertTrue(intr2.env == intr.env)


    def test_history(self):
        intr = Interpreter()
        res = intr.history([Flag('p')])
        self.assertTrue(res.print_out == True)
        self.assertTrue(res.message != None)

        intr.history([], Arg('on'))
        self.assertTrue(intr.maintain_history == True)

        intr.history([], Arg('off'))
        self.assertTrue(intr.maintain_history == False)

        intr.history([], Arg('toggle'))
        self.assertTrue(intr.maintain_history == True)


    def test_alias(self):
        intr = Interpreter()
        intr.alias([], Arg('run'), Arg('echo'), Arg('this'), Arg('t'))
        expected_json = {
            't':'run echo this'
        }
        self.assertTrue(expected_json == intr.parser.json())

        res = intr.alias([Flag('p')])
        self.assertTrue(res.print_out)
        self.assertTrue(res.status == 0)

