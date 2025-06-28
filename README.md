Some scripts that are useful to manage Moodle.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/nwolff/moodle-scripts)

# To run the scripts

## Install uv

https://docs.astral.sh/uv/getting-started/installation/

## Developing

    uv sync
    uv run ruff check
    uv run ruff format
    uv run mypy .

## Running

Set the schoolyear in _lib/schoolyear.py_

To run any script:

    uv run name-of-script.py
