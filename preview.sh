#! /bin/bash

# This script is used to preview the markdown file in the browser.
# It will automatically refresh the page when the markdown file is changed.

# Usage:
#   ./preview.sh [markdown file]

# If the markdown file is not specified, output the usage and exit.
if [ $# -eq 0 ]; then
    echo "Usage: ./preview.sh [markdown file]"
    exit 1
fi


# Check if the markdown file exists
if [ ! -f "$1" ]; then
    echo "File $1 does not exist."
    exit 1
fi

# Check if the markdown file is a markdown file
if [ "${1##*.}" != "md" ]; then
    echo "File $1 is not a markdown file."
    exit 1
fi

# Check if the markdown file is empty
if [ ! -s "$1" ]; then
    echo "File $1 is empty."
    exit 1
fi

# Check if the markdown file is readable
if [ ! -r "$1" ]; then
    echo "File $1 is not readable."
    exit 1
fi

# Extract the 
# path
# filename without extension
# filename with extension

path=$(dirname "$1")
filename=$(basename "$1")
filename_without_extension="${filename%.*}"
filename_with_extension="${filename}"

# copy ./mkdocs_preview_template.yml to ./mkdocs_preview.yml and replace the following:
# <path-to-preview-doc> with the path to the preview doc
# <filename-with-extension> with the filename with extension
# <filename-without-extension> with the filename without extension

sed -e "s|<path-to-preview-doc>|$path|g" \
    -e "s|<filename-with-extension>|$filename_with_extension|g" \
    -e "s|<filename-without-extension>|$filename_without_extension|g" \
    ./mkdocs_preview_template.yml > ./mkdocs_preview.yml

# Start the mkdocs server
mkdocs serve -f ./mkdocs_preview.yml

