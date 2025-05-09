import os
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from vector_store import VectorStore

prompt_template = (
    "You are a helpful assistant that answers questions based on the "
    "provided context from the user's notes and emails. Use the context to provide "
    "accurate and relevant answers. If the context doesn't contain enough information "
    "to answer the question, say so.\n\nContext: {context}\n\nQuestion: {question}"
    "\n\nAnswer:"
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"


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
    return chain.invoke({"query": query})


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
    return chain.invoke({"query": query})
