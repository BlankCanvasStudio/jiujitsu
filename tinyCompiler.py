import ast, copy
from collections import OrderedDict


class FunctionSymbol:
    def __init__(self, name, params, node):
        self.name = name
        self.params = params 
        # if len(self.params) != 1: raise ValueError("Functions must have only 1 parameter 'p'")
        self.node = node    
            # Actual code to be moved. Array of ast.X nodes
            # the text itself can be returned with: ast.unparse(FunctionSymbol.node)


class OrderEntry:
    def __init__(self, type_in, index, name, node):
        # type is going to be ast.X and index is self explanatory
        self.type = type_in 
        self.index = index
        self.name = name
        self.node = node


class PythonParser:
    def __init__(self, filename):
        self.filename = filename
        self.ast = None
        self.parse()
        self.func_table = OrderedDict()
        self.imports = []
        self.order = OrderedDict()

    def parse(self):
        text = open(self.filename).read()
        self.ast = ast.parse(text)
        return self.ast

    def dump(self):
        if self.ast is None: self.parse()
        return ast.dump(self.ast, indent=4)

    def build(self):    # Build function symbol table and store non-functional commands
        if self.ast is None: self.parse()
        for el in self.ast.body: 
            # This is the main section of the python file
            # Should be a bunch of functions and some commands if __main__ isn't used
            if (type(el) == ast.FunctionDef):
                new_entry = FunctionSymbol(el.name, el.args.args, el)
                if el.name in self.func_table: raise ValueError("Cannot repeat function definitions")
                self.func_table[el.name] = new_entry
                self.order[el.name] = OrderEntry(type_in=ast.FunctionDef, index=el.name, name=el.name, node=el)
            elif type(el) == ast.ClassDef:
                self.order[el.name] = OrderEntry(type_in=ast.ClassDef, index=el.name, name=el.name, node=el)
            elif type(el) == ast.Import or type(el) == ast.ImportFrom:
                # This is safe to move to the top so no order entry is inserted
                self.imports += [ el ]
            else:
                self.order[ast.unparse(el)] = OrderEntry(type_in=type(el), index=ast.unparse(el), name=ast.unparse(el), node=el)


class Compiler:
    def __init__(self, parser_filename, interpreter_filename, output_filename = ""):
        self.p_filename = parser_filename
        self.f_filename = interpreter_filename 
        self.p_parser = PythonParser(self.p_filename)
        self.f_parser = PythonParser(self.f_filename)
        self.output_filename = output_filename
        self.final_ast = ast.Module()


    def build(self):
        self.p_parser.build()
        self.f_parser.build()


        # Build the written imports section. This is going to be moved to top for convenience 
        all_imports = self.p_parser.imports + self.f_parser.imports
        seen = set()
        final_imports = [x for x in all_imports if ast.unparse(x) not in seen and not seen.add(ast.unparse(x))] # Unique with order preserved
            # This doesn't work


        # Build the new functions 
        translated_p_body = []
        for el in self.p_parser.order.values():
            new_node = copy.deepcopy(el.node)
            if el.type == ast.FunctionDef:
                short_name = el.name[2:]     # removes p_ from the front of the function name
                f_name = 'f_' + short_name
                if f_name in self.f_parser.func_table:
                    # Logic to do injection based on similarities in control flow
                    new_node.body += self.f_parser.func_table[f_name].node.body
            translated_p_body += [ new_node ]


        # Build the new body by zipping the interpreter and parser files together
        def last_similar_index(key):
            keys_arr = list(self.f_parser.order.keys())
            index = keys_arr.index(key)
            tmp_key = keys_arr[index]
            if tmp_key[:2] == 'f_': tmp_key = 'p_' + tmp_key[2:]
            while index >= 0 and (tmp_key not in list(self.p_parser.order.keys())): 
                index = index - 1
                tmp_key = keys_arr[index]
                if tmp_key[:2] == 'f_': tmp_key = 'p_' + tmp_key[2:]

            return list(self.p_parser.order.keys()).index(tmp_key) - 1  if tmp_key in list(self.p_parser.order.keys()) else 0     
                # Need the extra 1 cause indexing into python arrays? 
                # It works but idk why and I don't care to look into it. It's in god's hands now

        ordered_body = translated_p_body
        for key, value in reversed(self.f_parser.order.items()):
            if value.type == ast.FunctionDef:
                if key[0:2] == 'f_': key = 'p_' + key[2:]
            elif value.type != ast.ClassDef: # ie any other type which is unparse string encoded
                key = ast.unparse(value.node)
            
            if key not in self.p_parser.order.keys():
                insert_index = last_similar_index(key)
                ordered_body = ordered_body[:insert_index] + [ value.node ] + ordered_body[insert_index:]
            else:
                continue


        # Create the new module to save
        new_module = copy.deepcopy(self.p_parser.ast)
        new_module.body = final_imports + ordered_body


        # Write the new code into a file
        fd = open(self.output_filename, 'w')
        fd.write(ast.unparse(new_module))
        fd.close()
