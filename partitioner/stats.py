#python3
import cxxfilt
from symex import SymEx
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
import pprint
import symex
from z3 import *
load_dotenv()
symex= SymEx()
name = input("Enter run number (For example: klee-out-91): ")
name = name.strip()
if name == "q":
	exit()
print("Getting trace for: "+name)
#symex.get_trace(name)
summaries = symex.get_old_summary(name)

math_q = []
counter = 0

for summary in summaries:
	print("Counter :" +str(counter))
	current = summary[0] #Vector to ref
	if symex.has_math(current):
			math_q.append(current)
	counter = counter + 1

math_q_clean = []
for query in math_q:
	math_q_clean = math_q_clean + symex.filter_math(query)


from IPython import embed; embed()
