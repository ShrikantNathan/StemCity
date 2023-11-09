import os
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.retrievers import RePhraseQueryRetriever
from langchain.chains import RetrievalQA, RetrievalQAWithSourcesChain
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.chroma import Chroma
from typing import LiteralString, List, Union, Dict
from glob import glob
import openai
from random import choice
import json
from dotenv import load_dotenv

credentials = json.load(open(os.path.join(os.getcwd(), "file_config.json")))
os.environ["OPENAI_API_KEY"] = credentials["API_CREDS"]["OPENAI_KEY"]
openai.api_key = os.getenv('OPENAI_API_KEY')
load_dotenv()

extracted_text_root_dir = os.path.join(os.getcwd(), "filtered_text_versions")
extracted_text_title_folder = [magazine_folder for magazine_folder in os.listdir(extracted_text_root_dir)]

magazine_folder_path = os.path.join(extracted_text_root_dir, extracted_text_title_folder[2])
print(f'folder name ::', os.path.basename(magazine_folder_path))

document_loader = DirectoryLoader(magazine_folder_path, glob='./*.txt')

documents = document_loader.load()

txt_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=500)

texts = txt_splitter.split_documents(documents)

# Create the database and store the embeddings
persist_directory = 'stem_city_db'

# persist the db to disk
embeddings = OpenAIEmbeddings()
vectordb = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory=persist_directory)

#persist the database to disk
vectordb.persist()
vectordb = None

# Now we can load the persisted database from the disk, and use it as normal.
vectordb = Chroma(embedding_function=embeddings, persist_directory=persist_directory)

# query = "what is Northrop DSP specialized in and what do they do?"
# query_2 = "how much will I earn If I go for a Navy officer position?"
query = "tell me something about mark simmons."
# # Retrieve the stored database from the disk
retriever = vectordb.as_retriever()


def process_llm_response(response) -> Union[LiteralString, None]:
    print(response["result"])


print('selected_question ::', query)
docs = retriever.get_relevant_documents(query)

retriever = vectordb.as_retriever(search_kwargs={"k": len(docs)})

# make a chain
qa_chain = RetrievalQA.from_chain_type(llm=ChatOpenAI(openai_api_key=openai.api_key), retriever=retriever)
llm_response = qa_chain(query)
process_llm_response(llm_response)


# for question in random_questions:
#     print('selected_question ::', question)
#     docs = retriever.get_relevant_documents(question)

#     retriever = vectordb.as_retriever(search_kwargs={"k": len(docs)})

#     # make a chain
#     qa_chain = RetrievalQA.from_chain_type(llm=ChatOpenAI(openai_api_key=openai.api_key), retriever=retriever)
#     llm_response = qa_chain(question)
#     process_llm_response(llm_response)

# class StemCityDocumentLoaderChatResponseModel:
#     def __init__(self) -> None:
#         self.document_loader_directory = DirectoryLoader(glob("E:\Bulk Downloads\Republic Channel Transcripts")[0])
#         self.openai_key: LiteralString = openai.api_key()
