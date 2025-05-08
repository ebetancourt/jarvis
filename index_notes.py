#!/usr/bin/env python3
import os
import yaml
from typing import List
import glob
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

# Set TOKENIZERS_PARALLELISM to false to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_settings():
    """Load settings from settings.yml."""
    with open("settings.yml", "r") as file:
        return yaml.safe_load(file)


def load_documents(notes_path: str) -> List[Document]:
    """Load all markdown documents from the specified directory."""
    documents = []
    pattern = os.path.join(notes_path, "**/*.md")
    total_files = len(list(glob.glob(pattern, recursive=True)))
    print(f"Found {total_files} markdown files")

    for i, file_path in enumerate(glob.glob(pattern, recursive=True), 1):
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            documents.extend(loader.load())
            print(f"[{i}/{total_files}] Loaded: {file_path}")
        except Exception as e:
            print(f"Error loading {file_path}: {str(e)}")
            continue
    return documents


def main():
    # Load settings
    settings = load_settings()
    notes_path = settings["obsidian_notes_path"]

    if not os.path.exists(notes_path):
        print(f"Error: Notes directory not found at {notes_path}")
        return

    print(f"Loading documents from {notes_path}...")
    documents = load_documents(notes_path)
    print(f"Loaded {len(documents)} documents")

    if not documents:
        print("No documents were loaded successfully. Please check the errors above.")
        return

    # Split documents into chunks
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.get("chunk_size", 1000),
        chunk_overlap=settings.get("chunk_overlap", 200),
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    # Initialize embeddings
    print("Initializing embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        )
    )

    # Create and persist the database
    print("Creating Chroma database...")
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db",
    )


if __name__ == "__main__":
    main()
