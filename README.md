Some scripts that are useful to manage Moodle.

Runs on python3.9+, which is part of the mac command line developer tools that can be installed without being sudoer

# To run the scripts

## Virtual environment

If you don't have direnv installed on your computer you can manually create the virtual environment :

To create the virtualenv (you need to do this only once):

    python3 -m venv .venv

To enter the virtualenv:

    source .venv/bin/activate

## Installing dependencies

Once inside the virtualenv you should install the requirements like this:

    pip install -r requirements.txt

## Developing

    pip install -r dev-requirements.txt
    ruff check
    ruff format
    mypy .

## Running

Set the schoolyear in _lib/schoolyear.py_

All scripts are marked as executable, so you can just run them like this:

    ./name-of-script.py
