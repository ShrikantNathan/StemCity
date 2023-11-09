import os
from random import choice
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings import HuggingFaceInstructEmbeddings, OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader, DirectoryLoader, PyMuPDFLoader, PyPDFLoader
import json
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
import textwrap

original_mag_dir = os.path.join(os.getcwd(), "All Original Magazines")

doc_loaders = DirectoryLoader(original_mag_dir, glob='./*.pdf', loader_cls=PyMuPDFLoader)  # loader_cls=PyMuPDFLoader
documents = doc_loaders.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)

instructor_embeddings = HuggingFaceInstructEmbeddings(model_name='hkunlp/instructor-xl', model_kwargs={'device': 'cuda'})

persist_directory = 'stemcitydb'
vectordb = Chroma.from_documents(documents=texts, embedding=instructor_embeddings, persist_directory=persist_directory)

vectordb = Chroma(persist_directory=persist_directory, embedding_function=instructor_embeddings)

# Making a retriever
retriever = vectordb.as_retriever()

retriever = vectordb.as_retriever(search_kwargs={"k": 3})

credentials = json.load(open(os.path.join(os.getcwd(), "file_config.json")))
os.environ["OPENAI_API_KEY"] = credentials["API_CREDS"]["OPENAI_KEY"]
load_dotenv()

qa_chain = RetrievalQA.from_chain_type(llm=ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"), model='gpt-4'), chain_type="stuff", retriever=retriever, return_source_documents=True)

def wrap_text_preserve_newlines(text, width=110):
    lines = text.split('\n')
    wrapped_lines = [textwrap.fill(line, width=width) for line in lines]

    # Join the wrapped lines back together using newline characters
    wrapped_text = "\n".join(wrapped_lines)

    return wrapped_text

def process_llm_response(llm_response):
    print(f'{wrap_text_preserve_newlines(llm_response["result"])}\n')

# break it down
test_question_sets = {"Questions": ["what is Corning Incorporated specialized in, or what are they into?",
                                    "Tell me something about Pauline Bennett, Nancy-Kim Yu and Nora Lin",
                                    "Tell me the achievements of Alicia Abella",
                                    "tell me the address of career communications group?",
                                    "tell me in detail as to what does DoD or Department of Defense offer?",
                                    "What does Shell offer?",
                                    "What was Jian Chu's role and accomplishments?",
                                    "What did William state in her resume, and what was her role and accomplishments?",
                                    "what does AFRL offer?",
                                    "What was Janel Yellen's role?",
                                    "What does General Dynamics offer? or what are they specialized at?",
                                    "Tell me something in detail about Mary Teresa Barra"]}

for query in test_question_sets["Questions"]:
    # query = "what is Corning Incorporated specialized in, or what are they into?"
    llm_response = qa_chain(query)
    process_llm_response(llm_response)