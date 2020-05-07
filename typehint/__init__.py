import ast
import _ast
import inspect

class Declaration:
    def __init__(self, return_type, arg_types):
        self._return_type = return_type
        self._arg_types = arg_types
    
    def __repr__(self):
        return f'<{self._return_type}>' + \
               ''.join(f'[{arg}]' for arg in self._arg_types)

class TypeHints:
    def __init__(self):
        self._functions = {
            'int': Declaration('int', ()),
        }

    def declare_function(self, name, return_type, arg_types):
        self._functions[name] = Declaration(return_type, arg_types)

    def _usage_call(self, call, equals_to=None):
        assert type(call) == _ast.Call
        
        name = call.func.id
        if name in self._functions:
            return

        if equals_to is None:
            returns = 'void'
        else:
            returns = self.hint_node({}, equals_to)

        args = [self.hint_node(arg) for arg in call.args]
        self.declare_function(name, returns, args)

    def usage(self, f):        
        code = inspect.getsource(f.__code__)
        body = ast.parse(code).body[0].body
        
        for node in body:
            if type(node) == _ast.Expr:
                if type(node.value) == _ast.Compare:
                    self._usage_call(node.value.left, node.value.comparators[0])
                elif type(value) == _ast.Call:
                    self.usage_call(node.value.left)

    def _assign_node(self, vartypes, node, typename):
        if type(node) == _ast.Name:
            if node.id not in vartypes:
                vartypes[node.id] = typename
            elif vartypes[node.id] != typename:
                raise Exception('Multiple types for ' + node.id)
            return node.id

    def _ann_type(self, ann):
        if type(ann) == _ast.Name:
            return ann.id

    def _scan_node(self, vartypes, node):
        if type(node) == _ast.Assign:
            value_type = self.hint_node(vartypes, node.value)
            for target in node.targets[::-1]:
                if value_type is not None:
                    self._assign_node(vartypes, target, value_type)
                else:
                    value_type = self.hint_node(vartypes, target)
        elif type(node) == _ast.AnnAssign:
            self._assign_node(vartypes, node.target, self._ann_type(node.annotation))

    def hint_node(self, vartypes, node):
        if type(node) == _ast.Name:
            return vartypes.get(node.id)
        elif type(node) == _ast.Num:
            return type(node.n).__name__
        elif type(node) == _ast.Str:
            return 'str'
        elif type(node) == _ast.Call:
            return self._functions[node.func.id]._return_type

    def hint(self, f, args=()):
        source = inspect.getsource(f.__code__)
        if args and len(args) != f.__code__.co_argcount:
            raise Exception('Incorrect number of arguments')

        module = ast.parse(source)
        if not hasattr(module, 'body') or not module.body:
            raise Exception("Not body in parse function tree")

        if len(module.body) > 1:
            raise Exception("Too many child nodes in the root tree")

        func = module.body[0]
        if type(func) != _ast.FunctionDef:
            raise Exception('Root node is not a function')

        if not args:
            args = tuple(self._ann_type(arg.annotation) for arg in func.args.args)

        argnames = f.__code__.co_varnames[:f.__code__.co_argcount]
        vartypes = dict(zip(argnames, args))

        for node in func.body:
            self._scan_node(vartypes, node)
        
        return vartypes
