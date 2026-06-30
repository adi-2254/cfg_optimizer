import streamlit as st
import networkx as nx
from networkx.drawing.nx_pydot import to_pydot
from pycparser import c_parser
from main import CFGBuilder, optimize_constants, compute_live_variables, eliminate_dead_code, remove_unreachable_code
import re

st.set_page_config(layout="wide", page_title="CFG Optimizer Suite")
st.title("Compiler Middle-End Optimization Suite")

col1, col2 = st.columns(2)

with col1:
    st.header("1. Input C Code")
    default_code = """int main() {
    int w = 2 + 2;      
    int x = w + 10;     
    int dead_var = 99;  
    
    if (x > 5) {
        x = x + 1;
        return x;
    } else {
        x = x - 1;
        return x;
    }
    
    int ghost = 50; 
}"""
    code_input = st.text_area("Paste C code here:", value=default_code, height=400)
    analyze_btn = st.button("Run All Optimizations")

with col2:
    st.header("2. Optimized CFG")
    if analyze_btn:
        try:
            def sanitize_c_code(text):
                text = re.sub(r'//.*?$|/\*.*?\*/', '', text, flags=re.MULTILINE | re.DOTALL)
                text = re.sub(r'#.*', '', text)
                text = re.sub(r'__attribute__\s*\(\(.*?\)\)', '', text, flags=re.DOTALL)
                text = re.sub(r'\b__inline\b|\b__inline__\b|\binline\b', '', text)
                text = re.sub(r'\b__extension__\b', '', text)
                text = re.sub(r'\b__restrict\b|\b__restrict__\b', '', text)
                text = re.sub(r'\b__asm__\s*\(.*?\)', '', text, flags=re.DOTALL)
                return text
            
            clean_code = sanitize_c_code(code_input)
            
            parser = c_parser.CParser()
            ast = parser.parse(clean_code, filename='<none>')
            
            builder = CFGBuilder()
            builder.visit(ast)
            
            folded = optimize_constants(builder.cfg)
            compute_live_variables(builder.cfg)
            eliminated = eliminate_dead_code(builder.cfg)
            unreachable = remove_unreachable_code(builder.cfg)
            
            st.success(f"**Optimizations Complete!**\n\n"
                       f"✖ {folded} Constants Folded/Propagated\n\n"
                       f"✖ {eliminated} Dead Instructions Eliminated\n\n"
                       f"✖ {unreachable} Unreachable Blocks Removed")
            
            vis_graph = nx.DiGraph()
            for node, data in builder.cfg.nodes(data=True):
                label = f"{node}\n" + "\n".join(data['statements'])
                vis_graph.add_node(node, label=label, shape="box", style="filled", fillcolor="lightblue")
                
            for u, v, data in builder.cfg.edges(data=True):
                edge_label = data.get('label', '')
                vis_graph.add_edge(u, v, label=edge_label)
                
            pdot = to_pydot(vis_graph)
            st.graphviz_chart(pdot.to_string())
            
        except Exception as e:
            st.error(f"Error analyzing code: {type(e).__name__} - {e}")