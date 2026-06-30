import networkx as nx
from pycparser import c_parser, c_ast, c_generator
import re

class CFGBuilder(c_ast.NodeVisitor):
    def __init__(self):
        self.cfg = nx.DiGraph()
        self.current_block_statements = []
        self.block_counter = 0
        self.current_block_id = None
        self.generator = c_generator.CGenerator()

    def _create_new_block(self):
        block_id = f"Block_{self.block_counter}"
        self.block_counter += 1
        self.cfg.add_node(block_id, statements=[], defs=set(), uses=set(), live_in=set(), live_out=set())
        return block_id

    def _extract_uses(self, node):
        uses = set()
        class IDVisitor(c_ast.NodeVisitor):
            def visit_ID(self, id_node):
                uses.add(id_node.name)
        if node:
            IDVisitor().visit(node)
        return uses

    def visit_FuncDef(self, node):
        self.current_block_id = self._create_new_block()
        
        # Keep track of ALL function starting blocks so the 
        # Unreachable Code remover doesn't delete helper functions
        if 'function_entries' not in self.cfg.graph:
            self.cfg.graph['function_entries'] = []
        self.cfg.graph['function_entries'].append(self.current_block_id)
            
        self.visit(node.body)
        if self.current_block_statements:
            self.cfg.nodes[self.current_block_id]['statements'] = self.current_block_statements
        
        self.current_block_id = None
        self.current_block_statements = []

    def visit_Decl(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)

        if node.name:
            self.cfg.nodes[self.current_block_id]['defs'].add(node.name)
            if node.init:
                rhs_str = self.generator.visit(node.init)
                self.current_block_statements.append(f"Declare: {node.name} = {rhs_str}")
                self.cfg.nodes[self.current_block_id]['uses'].update(self._extract_uses(node.init))
            else:
                self.current_block_statements.append(f"Declare: {node.name}")
        self.generic_visit(node)

    def visit_DeclList(self, node):
        for decl in node.decls:
            self.visit(decl)

    def visit_Assignment(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)

        lval_str = self.generator.visit(node.lvalue)
        rhs_str = self.generator.visit(node.rvalue)
        self.current_block_statements.append(f"Assign: {lval_str} = {rhs_str}")

        if isinstance(node.lvalue, c_ast.ID):
            self.cfg.nodes[self.current_block_id]['defs'].add(node.lvalue.name)
            
        if node.rvalue:
            self.cfg.nodes[self.current_block_id]['uses'].update(self._extract_uses(node.rvalue))
        self.generic_visit(node)

    def visit_FuncCall(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)
            
        call_str = self.generator.visit(node)
        self.current_block_statements.append(f"Call: {call_str}")
        if node.args:
            self.cfg.nodes[self.current_block_id]['uses'].update(self._extract_uses(node.args))

    def visit_Return(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)

        if isinstance(node.expr, c_ast.ID):
            self.current_block_statements.append(f"Return: {node.expr.name}")
        else:
            self.current_block_statements.append("Return")
        if node.expr:
            self.cfg.nodes[self.current_block_id]['uses'].update(self._extract_uses(node.expr))
        self.generic_visit(node)

    def visit_If(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)

        cond_str = self.generator.visit(node.cond) if node.cond else ""
        self.current_block_statements.append(f"If ({cond_str})")
        if node.cond:
            self.cfg.nodes[self.current_block_id]['uses'].update(self._extract_uses(node.cond))
            
        entry_block = self.current_block_id
        self.cfg.nodes[entry_block]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []
        
        true_block = self._create_new_block()
        self.cfg.add_edge(entry_block, true_block, label="True")
        self.current_block_id = true_block
        self.visit(node.iftrue)
        self.cfg.nodes[true_block]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []
        last_true_block = self.current_block_id
        
        last_false_block = None
        if node.iffalse:
            false_block = self._create_new_block()
            self.cfg.add_edge(entry_block, false_block, label="False")
            self.current_block_id = false_block
            self.visit(node.iffalse)
            self.cfg.nodes[false_block]['statements'] = list(self.current_block_statements)
            self.current_block_statements = []
            last_false_block = self.current_block_id

        merge_block = self._create_new_block()
        self.cfg.add_edge(last_true_block, merge_block)
        if last_false_block:
            self.cfg.add_edge(last_false_block, merge_block)
        else:
            self.cfg.add_edge(entry_block, merge_block, label="False")
            
        self.current_block_id = merge_block

    def visit_While(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)

        cond_str = self.generator.visit(node.cond) if node.cond else ""
        self.current_block_statements.append(f"While ({cond_str})")
        if node.cond:
            self.cfg.nodes[self.current_block_id]['uses'].update(self._extract_uses(node.cond))
            
        entry_block = self.current_block_id
        self.cfg.nodes[entry_block]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []
        
        cond_block = self._create_new_block()
        self.cfg.add_edge(entry_block, cond_block)
        
        body_block = self._create_new_block()
        self.cfg.add_edge(cond_block, body_block, label="True")
        self.current_block_id = body_block
        
        self.visit(node.stmt)
        self.cfg.nodes[body_block]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []
        
        self.cfg.add_edge(body_block, cond_block, label="Loop Back")
        
        exit_block = self._create_new_block()
        self.cfg.add_edge(cond_block, exit_block, label="False")
        self.current_block_id = exit_block

    def visit_For(self, node):
        if self.current_block_id is None:
            return self.generic_visit(node)

        if node.init:
            self.visit(node.init) 

        entry_block = self.current_block_id
        self.cfg.nodes[entry_block]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []

        cond_block = self._create_new_block()
        self.cfg.add_edge(entry_block, cond_block)

        cond_str = self.generator.visit(node.cond) if node.cond else ""
        self.current_block_statements.append(f"For Cond ({cond_str})")
        if node.cond:
            self.cfg.nodes[cond_block]['uses'].update(self._extract_uses(node.cond))

        self.cfg.nodes[cond_block]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []

        body_block = self._create_new_block()
        self.cfg.add_edge(cond_block, body_block, label="True")
        self.current_block_id = body_block

        self.visit(node.stmt) 

        if node.next:
            self.visit(node.next)

        self.cfg.nodes[self.current_block_id]['statements'] = list(self.current_block_statements)
        self.current_block_statements = []

        self.cfg.add_edge(self.current_block_id, cond_block, label="Loop Back")

        exit_block = self._create_new_block()
        self.cfg.add_edge(cond_block, exit_block, label="False")
        self.current_block_id = exit_block

def optimize_constants(cfg):
    folded_count = 0
    for node, data in cfg.nodes(data=True):
        known_constants = {}
        optimized_statements = []
        
        for stmt in data['statements']:
            if "=" in stmt and "==" not in stmt:
                prefix, math_expr = stmt.split("=", 1)
                prefix = prefix.strip()
                math_expr = math_expr.strip()
                
                for var_name, var_val in known_constants.items():
                    math_expr = re.sub(fr'\b{var_name}\b', str(var_val), math_expr)
                
                try:
                    if re.match(r'^[\d\s\+\-\*\/\(\)]+$', math_expr):
                        result = int(eval(math_expr))
                        
                        if prefix.startswith("Assign:"):
                            var_name = prefix.replace("Assign:", "").strip()
                            known_constants[var_name] = result
                        elif prefix.startswith("Declare:"):
                            var_name = prefix.replace("Declare:", "").strip()
                            known_constants[var_name] = result
                            
                        stmt = f"{prefix} = {result}"
                        folded_count += 1
                except:
                    pass
                    
                optimized_statements.append(stmt)
            else:
                optimized_statements.append(stmt)
                
        data['statements'] = optimized_statements
    return folded_count

def compute_live_variables(cfg):
    nodes = list(cfg.nodes())
    changed = True
    while changed:
        changed = False
        for node in reversed(nodes):
            data = cfg.nodes[node]
            new_out = set()
            for succ in cfg.successors(node):
                new_out.update(cfg.nodes[succ]['live_in'])
            new_in = set(data['uses']).union(new_out - set(data['defs']))
            if new_in != data['live_in'] or new_out != data['live_out']:
                data['live_in'] = new_in
                data['live_out'] = new_out
                changed = True

def eliminate_dead_code(cfg):
    removed_count = 0
    for node, data in cfg.nodes(data=True):
        optimized_statements = []
        for stmt in data['statements']:
            if stmt.startswith("Assign:") or stmt.startswith("Declare:"):
                var_part = stmt.split("=")[0]
                var_name = var_part.split(":")[1].strip()
                
                if "[" in var_name or "*" in var_name:
                    optimized_statements.append(stmt)
                    continue
                
                if var_name not in data['live_out'] and var_name not in data['uses']:
                    removed_count += 1
                    continue
            optimized_statements.append(stmt)
        data['statements'] = optimized_statements
    return removed_count

def remove_unreachable_code(cfg):
    entries = cfg.graph.get('function_entries', [])
    if not entries:
        return 0
        
    reachable_nodes = set()
    
    for entry in entries:
        if entry in cfg:
            reachable_nodes.update(nx.descendants(cfg, entry))
            reachable_nodes.add(entry)
    
    all_nodes = set(cfg.nodes())
    unreachable_nodes = all_nodes - reachable_nodes
    
    count = len(unreachable_nodes)
    cfg.remove_nodes_from(unreachable_nodes)
    return count

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            c_code = f.read()
        
        clean_code = re.sub(r'//.*?$|/\*.*?\*/', '', c_code, flags=re.MULTILINE | re.DOTALL)
        clean_code = re.sub(r'#.*', '', clean_code)
        clean_code = re.sub(r'__attribute__\s*\(\(.*?\)\)', '', clean_code, flags=re.DOTALL)
        clean_code = re.sub(r'\b__inline\b|\b__inline__\b|\binline\b', '', clean_code)
        clean_code = re.sub(r'\b__extension__\b', '', clean_code)
        clean_code = re.sub(r'\b__restrict\b|\b__restrict__\b', '', clean_code)
        clean_code = re.sub(r'\b__asm__\s*\(.*?\)', '', clean_code, flags=re.DOTALL)
        
        parser = c_parser.CParser()
        ast = parser.parse(clean_code, filename='<none>')
        
        builder = CFGBuilder()
        builder.visit(ast)
        
        folded = optimize_constants(builder.cfg)
        compute_live_variables(builder.cfg)
        eliminated = eliminate_dead_code(builder.cfg)
        unreachable = remove_unreachable_code(builder.cfg)
        
        return {
            "status": "success", 
            "file": filepath, 
            "nodes_remaining": builder.cfg.number_of_nodes(), 
            "constants_folded": folded,
            "dead_code_removed": eliminated,
            "unreachable_blocks_removed": unreachable
        }
    except Exception as e:
        return {"status": "error", "file": filepath, "error_msg": str(e)}