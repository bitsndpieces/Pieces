#!/usr/bin/python3
import sys
import frontend
import clang.cindex
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
import json

@click.command()
@click.argument('conf', type=click.File('r'))
@click.argument('input', type=click.File('rb'))
@click.argument('output', type=click.File('wb'))
def inout(conf, input, output):
	input_file = input.name
	output_file = output.name
	return [json.load(conf), input_file, output_file]
	

# Function to add a new line at the beginning of each function
def add_line_to_functions(cursor):
	print(cursor.kind)
	for token in cursor.get_tokens():
		# Print token information
		print("Spelling:", token.spelling)
		print("Kind:", token.kind)
		print("Location:", token.location)
	if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
		# Get the location of the cursor
		location = cursor.location
		if location.file:
			# Get the function body
			function_body = cursor.get_children()
			fb = list(function_body)
			if function_body and fb[0].kind == clang.cindex.CursorKind.COMPOUND_STMT:
				# Get the first statement in the function body
				first_statement = fb[0].get_children()
				# Create a new cursor for the line "int a = 0;"

	# Recursively traverse children
	for child in cursor.get_children():
		add_line_to_functions(child)

def generate_source(cursor):
	# Generate the source code by traversing the AST
	generated_source = ''
	previous_token = None
	for token in cursor.get_tokens():

		# Check if the previous token exists and if it ends with a new line
		if previous_token and previous_token.location.line != token.location.line:
			# If the previous token ends with a new line, add it to the generated source
			generated_source += "\n"

		generated_source += token.spelling
		generated_source += " "

		# Update the previous token
		previous_token = token

	return generated_source

def main():
	load_dotenv()
	[config, input_file, output_file] = inout(standalone_mode=False)

	pp_f = frontend.preprocess(input_file,config["firmware"]["fronted_flags"], config["firmware"]["project_root"])
	tu = frontend.parse_c_program(pp_f.name)
	cursor = tu.cursor
	frontend.print_ast(cursor)
	frontend.find_functions(cursor)

	# Initialize libclang and parse the source file
	index = clang.cindex.Index.create()

	try:
		translation_unit = index.parse(input_file)
	except clang.cindex.TranslationUnitLoadError:
		print(f"Failed to load translation unit for {input_file}")
		return

	# Get the cursor for the translation unit
	cursor = translation_unit.cursor

	# Traverse the AST and add a new line to the beginning of each function
	add_line_to_functions(cursor)

	# Generate the modified source code
	modified_code = generate_source(cursor)

	# Write the modified code to the output file
	with open(output_file, 'w', encoding='utf-8') as f:
		f.write(modified_code)

	print(f"Modified source code written to {output_file}")

if __name__ == "__main__":
	main()

