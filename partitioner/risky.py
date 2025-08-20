#!/usr/bin/python3
import frontend
import shutil
import ec_loader
import click
import utils
import sys
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

os.environ["P_OUT_DIR"] = os.path.abspath(os.environ["P_OUT_DIR"]) +"/"
os.makedirs(os.environ["P_OUT_DIR"], exist_ok=True)
input["firmware"]["bc"] =  os.path.abspath(input["firmware"]["bc"])
debug("Loading input firmware.")
compiler = Compiler()
compiler.analyze(input["firmware"])

firmware = ec_loader.Firmware(input["firmware"])

print("Here")
symex = symex.SymEx()
#fun = "_ZN6AC_PID8update_iEfb"
fun = "_ZN6AC_PID10update_allEfffbf"
#fun = "pid_calculate"
summaries = symex.generate_summary(firmware, fun)

math_q = symex.filter_queries_with_math(summaries)

only_math_q = []
for q in math_q:
	only_math_q = only_math_q + symex.filter_math(q)


sir = []
for q in only_math_q:
	if not "..."  in str(q):
		sir.append(symex.super_simple(q))

for path in sir:
	if len(symex.get_addends(path)) ==3:
		print(path)
		break

		

from IPython import embed; embed()
