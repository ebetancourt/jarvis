#!/usr/bin/env python3
from search_tools import search_notes, search_gmail
from dotenv import load_dotenv

load_dotenv()

notes = search_notes.invoke("What did I write about Chris Pratt's workout?")
emails = search_gmail.invoke("When does my Obsidian Sync renewal come up?")

print("")
print("")
print("Notes:")
for note in notes:
    print(f"Item: {note['item']}")
    print(f"Bucket: {note['bucket']}")
    print(f"Source: {note['source']}")
    print(f"Distance: {note['distance']}")
    print("")

print("")
print("")
print("Gmail:")
for email in emails:
    print(f"Item: {email['item']}")
    print(f"Bucket: {email['bucket']}")
    print(f"Source: {email['source']}")
    print(f"Distance: {email['distance']}")
    print("")
