#!/bin/bash

# Script takes a single argument which is the path to setup.py
# If path is not supplied then default to ./
if [[ -z $1 ]]; then path="."; else path=$1; fi

if [[ ! -f "$path/setup.py" ]]
  then
    echo -e "\033[1;31mError: File setup.py not found at $path/\033[0m"
    exit
fi

echo -e "\033[1;36mGenerating requirements.txt file for core dependencies.\033[0m"
echo "- Generating temp file"
pip freeze --exclude-editable >> $path/temp-requirements.txt
echo "- Uninstalling existing packages"
pip uninstall -y -q -r $path/temp-requirements.txt
echo "- Upgrading pip to latest version"
python -m pip install --quiet --upgrade pip
echo "- Installing core dependencies only"
pip install -q -e $path/.
echo "- Freezing core dependencies and writing to $path/requirements.txt"
pip freeze --exclude-editable >| $path/requirements.txt
echo "- Restoring all packages"
pip install -q -r $path/temp-requirements.txt
echo "- Removing temp file"
rm $path/temp-requirements.txt
echo "- Finished! 🎉"
