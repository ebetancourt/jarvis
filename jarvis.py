#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()
import json
import argparse
import sys

from search_tools import search_notes, search_gmail

notes = search_notes.invoke("What did I write about Chris Pratt's workout?");
emails = search_gmail.invoke("Obsidian Sync`");

print("")
print("")
print("Notes:")
print(notes)

print("")
print("")
print("Gmail:")
print(emails)
