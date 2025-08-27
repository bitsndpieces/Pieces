import networkx as nx
from networkx.drawing.nx_pydot import read_dot
import pydot

import re
import sys
import os

import subprocess

class Analysis:
    def __init__(self):
        self.cfg = None
        self.pddg = None
        self.pdg = None

analysis = Analysis()

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

def merge_graphs(dg, cg):
    pdg = nx.DiGraph()
    pdg.add_nodes_from(dg.nodes(data=True))
    pdg.add_nodes_from(cg.nodes(data=True))

    for u, v, data in dg.edges(data=True):
        if 'type' in dg.nodes[u] and dg.nodes[u]['type'] == 'function':
            pdg.add_edge(u, v, dep="control", **data)
        else:
            pdg.add_edge(u, v, dep="data", **data)

    for u, v, data in cg.edges(data=True):
        if 'type' in cg.nodes[u] and cg.nodes[u]['type'] == 'function':
            pdg.add_edge(u, v, dep="control", **data)
        else:
            pdg.add_edge(u, v, dep="data", **data)

    return pdg

def replace_node(G, old_node, new_node):
    G.add_node(new_node, **G.nodes[old_node])

    if (isinstance(G, nx.MultiDiGraph)):
        for pred in G.predecessors(old_node):
            if not pred == new_node:
                for key, attr in G[pred][old_node].items():
                    G.add_edge(pred, new_node, key=key, **attr)
        for succ in G.successors(old_node):
            if not succ == new_node:
                for key, attr in G[old_node][succ].items():
                    G.add_edge(new_node, succ, key=key, **attr)

    elif (isinstance(G, nx.DiGraph)):
        for pred in list(G.predecessors(old_node)):
            if not pred == new_node:
                attr = G.get_edge_data(pred, old_node)
                G.add_edge(pred, new_node, **attr)
        for succ in list(G.successors(old_node)):
            if not succ == new_node:
                attr = G.get_edge_data(old_node, succ)
                G.add_edge(new_node, succ, **attr)

    G.remove_node(old_node)

def load_cfg_light(config):
    path = "./out/light-cfg.dot"
    cmd = ["opt", "-enable-new-pm=0", "-dot-callgraph", "-disable-output", config["bc"]]
    subprocess.run(cmd)
    cmd = ["cp", config["bc"] + ".callgraph.dot", path]
    subprocess.run(cmd)

    cfg = read_dot(path)
    cmd = ["rm", path]
    subprocess.run(cmd)

    for n in list(cfg.nodes(data=True)):
        # fun = '"{function_name}"'
        if ("label" in n[1]):
            fun = n[1]["label"][2:-2]
            replace_node(cfg, n[0], fun)
            cfg.nodes[fun]['type'] = 'function'

    return cfg

def load_cfg_svf(config):
    path = "./out/icfg_initial.dot"
    cmd = [os.environ["SVF"], config["bc"], "-dump-icfg"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL)

    cmd = ["cp", "./icfg_initial.dot", path]
    subprocess.run(cmd)

    cmd = ["rm", "./icfg_initial.dot"]
    subprocess.run(cmd)
    
    cfg = read_dot(path)
    cmd = ["rm", path]
    subprocess.run(cmd)

    for n in list(cfg.nodes(data=True)):
        name = n[0]
        if ':' in name:
            name = name.split(':')[0]
            replace_node(cfg, n[0], name)
    for n in list(cfg.nodes(data=True)):
        if ("label" in n[1]):
            if "GlobalICFGNode" in n[1]["label"]:
                continue
            elif any(sub in n[1]["label"] for sub in ["CallICFGNode", "RetICFGNode"]):
                caller = n[1]["label"].split("{fun: ")[1].split('\\')[0]
                replace_node(cfg, n[0], caller)
                cfg.nodes[caller]['type'] = 'function'

                callee = n[1]["label"].split("call")[1]
                if '@' in callee and '(' in callee:
                    callee = callee.split('@')[1].split('(')[0]
                else:
                    continue
                cfg.add_edge(caller, callee)
                cfg.nodes[callee]['type'] = 'function'
            elif "{fun: " in n[1]["label"]:
                fun = n[1]["label"].split('{fun: ')[1].split('\\')[0]
                replace_node(cfg, n[0], fun)
                cfg.nodes[fun]['type'] = 'function'
    
    new_cfg = nx.DiGraph()
    functions = [(n, d) for n, d in cfg.nodes(data=True) if d.get("type") == 'function']

    new_cfg.add_nodes_from(functions)

    for f1 in functions:
        reachable = nx.descendants(cfg, f1[0])
        for f2 in functions:
            if f2[0] in reachable:
                new_cfg.add_edge(f1[0], f2[0])

    return new_cfg

def load_ddg_light(config):
    path = "./out/light-ddg.dot"
    cmd = [os.environ["SVF_BIN"] + "/svf-pieces", f'bc={config["bc"]}', f'ddg={path}', '-use-def', '-ffmap', '-get-threads']
    subprocess.run(cmd)
    
    ddg = read_dot(path)
    cmd = ["rm", path]
    subprocess.run(cmd)

    for n in list(ddg.nodes(data=True)):
        if ("label" in n[1]):
            data = n[1]["label"]
            replace_node(ddg, n[0], data)

    return ddg

def load_ddg_svf(config):
    # first, generate the different maps
    cmd = [os.environ["SVF_BIN"] + "/svf-pieces", f'bc={config["bc"]}', '-ffmap', '-use-def']
    subprocess.run(cmd)

    path = "./out/svfg_final.dot"
    cmd = [os.environ["SVF"], config["bc"], "-dump-vfg", "-get-threads"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL)

    cmd = ["cp", "./svfg_final.dot", path]
    subprocess.run(cmd)

    cmd = ["rm", "./svfg_final.dot"]
    subprocess.run(cmd)
    
    ddg = read_dot(path)
    cmd = ["rm", path]
    subprocess.run(cmd)

    potential_links = []
    for n in list(ddg.nodes(data=True)):
        name = n[0]
        if ':' in name:
            name = name.split(':')[0]
            replace_node(ddg, n[0], name)
    for n in list(ddg.nodes(data=True)):
        if ("label" in n[1]):
            if "AddrVFGNode" in n[1]["label"] and 'GlobalValVar' in n[1]["label"]:
                data = n[1]["label"].split('@')[1].split(' ')[0]
                replace_node(ddg, n[0], data)
                ddg.nodes[data]["type"] = 'global'
            elif "IntraPHIVFGNode" in n[1]["label"]:
                spos = n[1]["label"].find("@")
                lpos = n[1]["label"].find("%")
                if (not spos == -1) and (spos < lpos or lpos == -1):
                    symbols = n[1]["label"].split("@")
                    try:
                        fun = symbols[1].split('(')[0]
                    except:
                        print(n[1]["label"])
                        exit()
                    for i in range(2, len(symbols)):
                        ref = symbols[i].split(',')[0]
                        if '(' in ref:
                            ref = ref.split('(')[0]
                        potential_links += [(ref, fun)]
            elif "ActualRetVFGNode" in n[1]["label"]:
                continue
                if not "@" in n[1]["label"]:
                    continue
                fun = n[1]["label"].split("@")[1].split("(")[0]
                replace_node(ddg, n[0], fun)
                ddg.nodes[fun]["type"] = 'function'
            elif any(sub in n[1]["label"] for sub in ["FormalParmVFGNode", "FormalRetVFGNode"]) and "Fun[" in n[1]["label"]:
                fun = n[1]["label"].split("Fun[")[1].split("]")[0]
                replace_node(ddg, n[0], fun)
                ddg.nodes[fun]["type"] = 'function'
            elif "{fun: " in n[1]["label"]:
                fun = n[1]["label"].split('{fun: ')[1].split('\\')[0]
                replace_node(ddg, n[0], fun)
                ddg.nodes[fun]["type"] = 'function'

    new_ddg = nx.DiGraph()
    globals = [(n, d) for n, d in ddg.nodes(data=True) if d.get("type") == 'global']
    functions = [(n, d) for n, d in ddg.nodes(data=True) if d.get("type") == 'function']

    new_ddg.add_nodes_from(globals)
    new_ddg.add_nodes_from(functions)

    for g in globals:
        reachable = nx.descendants(ddg, g[0])
        for f in functions:
            if f[0] in reachable:
                new_ddg.add_edge(g[0], f[0])
    #for f1 in functions: // this isn't really the job of the ddg
    #    reachable = nx.descendants(ddg, f1[0])
    #    for f2 in functions:
    #        if f2[0] in reachable:
    #            new_ddg.add_edge(f1[0], f2[0])
    for link in potential_links:
        if link[0] in new_ddg.nodes:# and new_ddg.nodes[link[0]]['type'] == 'global':
            new_ddg.add_edge(link[0], link[1])

    return new_ddg

def load_cfg(config):
    global analysis

    level = int(os.environ['ANALYSIS_LEVEL'])
    if level < 50: # do light analysis
        analysis.cfg = load_cfg_light(config)
    else: # do svf analysis
        analysis.cfg = load_cfg_svf(config)

def load_ddg(config):
    global analysis

    level = int(os.environ['ANALYSIS_LEVEL'])
    if level < 50: # do light analysis
        analysis.pddg = load_ddg_light(config)
    else: # do svf analysis
        analysis.pddg = load_ddg_svf(config)

def generate_pdg(cfg, ddg):
    pdg = merge_graphs(ddg, cfg)

    #pydot_graph = convert_to_pydot_safe(pdg)
    #pydot_graph.write_raw("pdg_combined.dot")

    return pdg

def run_analysis(config):
    global analysis

    load_cfg(config)
    load_ddg(config)

    analysis.pdg = generate_pdg(analysis.cfg, analysis.pddg)

    return analysis

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        dg = read_dot(sys.argv[1])
        cg = read_dot(sys.argv[2])

        print(dg.graph["graph"]["label"])
        print(cg.graph["graph"]["label"])

        pdg = merge_graphs(dg, cg)

        pdot_graph = convert_to_pydot_safe(pdg)
        pdot_graph.write_raw("pdg_combined.dot")

        print("✅ PDG written to: pdg_combined.dot")

