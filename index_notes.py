import yaml
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os
import glob

# Load settings from settings.yml
with open("settings.yml", "r") as file:
    settings = yaml.safe_load(file)

obsidian_notes_path = settings["obsidian_notes_path"]

# Find all markdown files recursively
pattern = os.path.join(obsidian_notes_path, "**/*.md")
markdown_files = glob.glob(pattern, recursive=True)

# Load and process each markdown file
documents = []
for file_path in markdown_files:
    try:
        loader = TextLoader(file_path)
        documents.extend(loader.load())
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")

# Split documents into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)

# Initialize embeddings with explicit model name
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# Create a Chroma database and store the documents
db = Chroma.from_documents(texts, embeddings, persist_directory="./chroma_db")

print(f"Successfully processed {len(markdown_files)} files.")
print("Notes indexed and stored in Chroma database.")
