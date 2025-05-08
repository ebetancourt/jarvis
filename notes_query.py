#!/usr/bin/env python3
import argparse
import os
import yaml
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
import json
from datetime import datetime

# Prompt template for both chain and logging
prompt_template = """You are a helpful assistant that answers questions based on the
provided context from the user's notes. Use the context to provide accurate and
relevant answers. If the context doesn't contain enough information to answer the
question, say so.

Context: {context}

Question: {question}

Answer:"""

# Set TOKENIZERS_PARALLELISM to false to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_settings():
    """Load settings from settings.yml."""
    with open("settings.yml", "r") as file:
        return yaml.safe_load(file)


def load_db():
    """Load the Chroma database with embeddings."""
    settings = load_settings()
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        )
    )
    return Chroma(persist_directory="./chroma_db", embedding_function=embeddings)


def create_chain():
    """Create a chain that combines retrieval and generation."""
    db = load_db()
    retriever = db.as_retriever(search_kwargs={"k": 5})

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7, max_tokens=1000)

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def get_api_key():
    """Get OpenAI API key from environment variable, .env file, or settings.yml."""
    # First try environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Then try .env file
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Finally try settings.yml
    settings = load_settings()
    api_key = settings.get("openai_api_key")
    if api_key:
        return api_key

    return None


def format_source(source):
    """Format the source path to be more readable."""
    if isinstance(source, str):
        return source
    elif isinstance(source, dict):
        return source.get("source", "Unknown source")
    return "Unknown source"


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Query your Obsidian notes using natural language."
    )
    parser.add_argument(
        "question", type=str, help="The question to ask about your notes"
    )
    args = parser.parse_args()

    # Check for OpenAI API key
    api_key = get_api_key()
    if not api_key:
        print("Error: OpenAI API key not found. Please set it in one of these ways:")
        print("1. Environment variable: export OPENAI_API_KEY='your-key'")
        print("2. .env file: Create a .env file with OPENAI_API_KEY=your-key")
        print("3. settings.yml: Add openai_api_key: your-key to settings.yml")
        return

    try:
        # Create the chain
        chain = create_chain()

        # Get the answer
        result = chain.invoke({"query": args.question})

        # Print the answer
        print("\nAnswer:")
        print(result["result"])

        # Prepare sources (de-duplicated)
        seen = set()
        unique_sources = []
        for doc in result["source_documents"]:
            if isinstance(doc, Document):
                source = doc.metadata.get("source", "Unknown source")
            else:
                source = format_source(doc)
            if source not in seen:
                seen.add(source)
                unique_sources.append(source)

        # Print sources
        print("\nSources:")
        for source in unique_sources:
            print(f"- {source}")

        # Log to query_log.json
        log_entry = {
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": args.question,
            "prompt": prompt_template.format(
                context="\n\n".join(
                    [doc.page_content for doc in result["source_documents"]]
                ),
                question=args.question,
            ),
            "response": result["result"],
            "sources": unique_sources,
        }
        with open("query_log.json", "a") as log_file:
            log_file.write(json.dumps(log_entry, indent=2))
            log_file.write("\n\n")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        print("\nDetailed error:")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
