#!/usr/bin/python3
import shutil
import os
import sys
import buildutils

def copy_with_overlay_extension(file_path):
	"""
	Copies a file and appends `.overlay` to the end of the original filename.

	Args:
		file_path (str): The path to the original file.

	Returns:
		str: The path to the copied file with the `.overlay` extension.
	"""
	if not os.path.isfile(file_path):
		raise FileNotFoundError(f"The file '{file_path}' does not exist.")

	# Get the directory and filename components
	directory, filename = os.path.split(file_path)
	
	# Append `.overlay` to the filename
	filename = filename.replace(".ld", "")
	new_filename = filename + ".overlay"
	new_file_path = os.path.join(directory, new_filename)

	# Copy the file to the new location
	shutil.copyfile(file_path, new_file_path)

	return new_file_path

# Example usage
if __name__ == "__main__":
	env = buildutils.load_project_meta()
	
	if buildutils.get_val(env, "LD_OVERLAY") == None:
		if len(sys.argv) != 2:
			print("Usage: python overlay_gen.py <file_path>")
			sys.exit(1)

		try:
			original_file = sys.argv[1]  # File path supplied as a command line argument
			copied_file = copy_with_overlay_extension(original_file)
			print(f"File copied to: {copied_file}")
			env["LD_OVERLAY"] = copied_file
			buildutils.save_project_meta(env)
		except Exception as e:
			print(f"Error: {e}")

