Some scripts that are useful for the job.

Require python3.9+, which is part of the mac command line developer tools that can be installed without being sudoer


# Running the scripts

## Virtual environment

Some of the scripts need dependencies to run, you'll know because the script directory will contain both `requirement.txt` and `.envrc` files.

If you don't have direnv installed on your computer you can manually create the virtual environment :


To create the virtualenv (you need to do this only once):

    python3 -m venv .


To enter the virtualenv:

    source bin/activate

## Installing dependencies

Once inside the virtualenv you should install the requirements like this:

    pip install -r requirements.txt


## Running

The scripts are marked as executable, so you can just run them like this:

    ./name-of-script.py


## Developing

black and isort are used to automatically format the code
