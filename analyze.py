from analyzer.gen_pdg import *
from dotenv import load_dotenv

def run(bc):
    return run_analysis(bc)

if __name__ == "__main__":
    load_dotenv()
    if len(sys.argv) >= 2:
        analysis = run_analysis(sys.argv[1])

        pdot_graph = convert_to_pydot_safe(analysis.cfg)
        pdot_graph.write_raw("out/cfg.dot")

        pdot_graph = convert_to_pydot_safe(analysis.pddg)
        pdot_graph.write_raw("out/pddg.dot")

        pdot_graph = convert_to_pydot_safe(analysis.pdg)
        pdot_graph.write_raw("out/pdg.dot")
