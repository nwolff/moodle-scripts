#!/usr/bin/python3

"""
Given a top-level directory, recursively renames all contained files and directories so that the names obey the rules of onedrive 
(and so the directory can be uploaded to onedrive without error)
"""
import os
import argparse
import os.path
import re

# https://support.microsoft.com/en-us/office/restrictions-and-limitations-in-onedrive-and-sharepoint-64883a5d-228e-48f5-b3d2-eb39e07630fa#invalidfilefoldernames
# Also trailing spaces that are not documented but fail when using the onedrive finder extension
forbidden = re.compile(r"^\s|\*|:|<|>|\?|/|\\|\||\s$")


def sanitized_path_element(path_element):
    return forbidden.sub("_", path_element)


def sanitize_filenames(root):
    """
    Recurse into root and sanitize the names of all files and directories inside
    """

    # Walk bottom-up because renaming files before renaming the enclosing directory seems safer than the opposite
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # Avoid sanitized name collision which would result in loss of files
        sanitized_names_in_dir = []

        for name in dirnames + filenames:
            sanitized_name = sanitized_path_element(name)

            # Overly simple collision avoidance algorithm, but we expect collisions to be rare
            while sanitized_name in sanitized_names_in_dir:
                sanitized_name = "_" + sanitized_name
            sanitized_names_in_dir.append(sanitized_name)

            if sanitized_name != name:
                src_path = os.path.join(dirpath, name)
                dst_path = os.path.join(dirpath, sanitized_name)
                print(f"  Renaming \t{src_path}\n\tto\t{dst_path}\n")
                os.rename(src_path, dst_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Normalizes names of files and directories to make them compatible with onedrive rules"
    )
    parser.add_argument(
        "root",
        metavar="ROOT DIR",
        help="The root directory containing the files to rename",
    )
    args = parser.parse_args()
    sanitize_filenames(args.root)
