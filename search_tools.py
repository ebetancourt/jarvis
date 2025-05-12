import os
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from common.vector_store import VectorStore

prompt_template = (
    "You are a helpful assistant that answers questions based on the "
    "provided context from the user's notes and emails. Use the context to provide "
    "accurate and relevant answers. If the context doesn't contain enough information "
    "to answer the question, say so.\n\nContext: {context}\n\nQuestion: {question}"
    "\n\nAnswer:"
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def get_source_key(doc):
    # Returns a stable key for deduplication
    try:
        if hasattr(doc, 'metadata'):
            meta = doc.metadata
            if meta.get("source") == "obsidian":
                return ("obsidian", meta.get("item") or meta.get("file_path") or str(doc))
            elif meta.get("source") == "Gmail":
                return ("gmail", meta.get("subject") or meta.get("item") or str(doc))
        if isinstance(doc, dict):
            if doc.get("source") == "obsidian":
                return ("obsidian", doc.get("item") or doc.get("file_path") or str(doc))
            elif doc.get("source") == "Gmail":
                return ("gmail", doc.get("subject") or doc.get("item") or str(doc))
        if isinstance(doc, str):
            return ("str", doc)
    except Exception:
        pass
    return ("other", str(doc))

def deduplicate_documents(documents):
    seen = set()
    unique_docs = []
    for doc in documents:
        key = get_source_key(doc)
        if key not in seen:
            seen.add(key)
            unique_docs.append(doc)
    return unique_docs

def load_db():
    from notes_query import load_settings

    settings = load_settings()
    vector_store = VectorStore(
        persist_directory="./chroma_db",
        embedding_model=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        ),
    )
    vector_store.load()
    return vector_store


def search_notes(query: str, k: int = 5):
    vector_store = load_db()
    retriever = vector_store.get_notes_retriever(search_kwargs={"k": k})
    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7, max_tokens=1000)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    result = chain.invoke({"query": query})
    # Deduplicate source_documents before returning
    if "source_documents" in result:
        result["source_documents"] = deduplicate_documents(result["source_documents"])
    return result


def search_gmail(query: str, k: int = 5):
    vector_store = load_db()
    retriever = vector_store.get_gmail_retriever(search_kwargs={"k": k})
    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7, max_tokens=1000)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    result = chain.invoke({"query": query})
    # Deduplicate source_documents before returning
    if "source_documents" in result:
        result["source_documents"] = deduplicate_documents(result["source_documents"])
    return result
