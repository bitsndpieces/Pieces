#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <program> <destination_folder>"
    exit 1
fi

PROGRAM=$1
DEST_FOLDER=$2

# Create the destination folder if it does not exist
mkdir -p "$DEST_FOLDER"

# Get the list of dependencies and copy them to the destination folder
ldd "$PROGRAM" | awk '{ if (match($3, "/")) print $3 }' | while read -r lib; do
    cp -v "$lib" "$DEST_FOLDER"
done


rm "$DEST_FOLDER"/libgcc_s.so.1 "$DEST_FOLDER"/libm.so.6 "$DEST_FOLDER"/libstdc++.so.6 "$DEST_FOLDER"/libc.so.6 "$DEST_FOLDER"/libpthread.so.0 "$DEST_FOLDER"/libdl.so.2  "$DEST_FOLDER"/libtcmalloc.so.4 "$DEST_FOLDER"/libsqlite3.so.0 "$DEST_FOLDER"/libtinfo.so.6  "$DEST_FOLDER"/libunwind.so.8

echo "All dependencies copied to $DEST_FOLDER"

