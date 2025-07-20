import networkx as nx
from networkx.drawing.nx_pydot import read_dot
import pydot

def quote_if_needed(s):
    """Quote strings that contain special DOT characters."""
    if isinstance(s, str) and (':' in s or ' ' in s or '-' in s):
        return f'"{s}"'
    return s

def convert_to_pydot_safe(graph):
    pdot = pydot.Dot(graph_type='digraph')

    for n, attrs in graph.nodes(data=True):
        n_quoted = quote_if_needed(n)
        clean_attrs = {k: quote_if_needed(v) for k, v in attrs.items()}
        pdot.add_node(pydot.Node(n_quoted, **clean_attrs))

    for u, v, attrs in graph.edges(data=True):
        u_quoted = quote_if_needed(u)
        v_quoted = quote_if_needed(v)
        clean_attrs = {k: quote_if_needed(v) for k, v in attrs.items()}
        pdot.add_edge(pydot.Edge(u_quoted, v_quoted, **clean_attrs))

    return pdot

def merge_graphs(svfg, icfg):
    pdg = nx.DiGraph()
    pdg.add_nodes_from(svfg.nodes(data=True))
    pdg.add_nodes_from(icfg.nodes(data=True))

    for u, v, data in svfg.edges(data=True):
        pdg.add_edge(u, v, dep="data", **data)

    for u, v, data in icfg.edges(data=True):
        pdg.add_edge(u, v, dep="control", **data)

    return pdg

if __name__ == "__main__":
    svfg = read_dot("svfg_final.dot")
    icfg = read_dot("icfg_initial.dot")

    pdg = merge_graphs(svfg, icfg)

    pdot_graph = convert_to_pydot_safe(pdg)
    pdot_graph.write_raw("pdg_combined.dot")

    print("✅ PDG written to: pdg_combined.dot")

