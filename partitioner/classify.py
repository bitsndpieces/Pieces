#!/usr/bin/python3
from IPython import embed
import frontend
import shutil
import ec_loader
import click
import utils
import sys
#from cpp_demangle import demangle
from utils import debug, print_help_msg
from dotenv import load_dotenv
from llvm import Compiler
import os
import symex

load_dotenv()
try:
    input = utils.load_config(standalone_mode=False)
    if not input:
        exit()
except Exception as e:
    print(e)
    utils.print_help_msg(utils.load_config)
    exit()

os.environ["P_OUT_DIR"] = os.path.abspath(os.environ["P_OUT_DIR"]) + "/"
os.makedirs(os.environ["P_OUT_DIR"], exist_ok=True)
input["firmware"]["bc"] = os.path.abspath(input["firmware"]["bc"])
debug("Loading input firmware.")
compiler = Compiler()
compiler.analyze(input["firmware"])

firmware = ec_loader.Firmware(input["firmware"])
symex = symex.SymEx()
symex.threshold = 10
symex.void_inline = False

fun = "_ZN6AC_PID8update_iEfb"
#fun = sys.argv[2]

# fun = "_ZN6AC_PID10update_allEfffbf"
summaries = symex.generate_summary(firmware, fun)

math_q = symex.filter_queries_with_math(summaries)

only_math_q = []
for q in math_q:
    only_math_q = only_math_q + symex.filter_math(q)

sir = []
for q in only_math_q:
    # print("---------------------------------------")
    # print(q)
    # print("---------------------------------------")
    # if "ZeroExt" not in str(q):  # TODO: remove temporary fix

    # sir.append(symex.super_simple(q))
    simple = symex.super_simple(q)
    print(f"Found function with constraints: ({simple})")
    print(f"Full Constraints: ")
    print(q)
    break
