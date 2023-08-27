# Funktioniert mit lokalem start night
# from src.dtos.ISayHelloDto import ISayHelloDto
import os
import pathlib

import pinecone
from decouple import config
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi import Form
from fastapi.middleware.cors import CORSMiddleware
from langchain import HuggingFaceHub
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings, HuggingFaceHubEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain.vectorstores import Pinecone
from typing_extensions import Annotated
from langchain.agents import Tool
from langchain.agents import initialize_agent
# sentence-transformers can not be used because it wont deploy on vercel

load_dotenv()

DESTINATION = "\\files\\"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World from src/index"}

@app.post("/pinecone/chatbot", status_code=200)
async def chatbot(
        query: Annotated[str, Form()]
):
    print("Start chat with %s " % f"{query}")
    apiKey = config('PINECONE_API_KEY')
    indexName = config('PINECONE_INDEX')
    environment = config('PINECONE_ENVIRONMENT')
    metric = "cosine"
    modelName = "all-MiniLM-L6-v2"
    #model = getModel(modelName)

    index = getAndCreateIndex(indexName, apiKey, environment, metric)

    embeddings = HuggingFaceEmbeddings(
         model_name="all-MiniLM-L6-v2"
    )

    text_field = "text"
    vectorstore = Pinecone(
        index, embeddings.embed_query, text_field
    )

    llm=HuggingFaceHub(repo_id="bigscience/bloom", model_kwargs={"temperature":1e-10})
    #https://python.langchain.com/docs/integrations/llms/huggingface_hub
    #llm=HuggingFaceHub(repo_id="google/flan-t5-xl", model_kwargs={"temperature":1e-10})
    #llm=HuggingFaceHub(repo_id="google/flan-ul2", model_kwargs={"temperature":1e-10})
    #llm=HuggingFaceHub(repo_id="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={"temperature":1e-10})
    #llm=HuggingFaceHub(repo_id="Xenova/gpt-3.5-turbo", model_kwargs={"temperature":1e-10})

    conversational_memory = ConversationBufferWindowMemory(
        memory_key='chat_history',
        k=5,
        return_messages=True
    )
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )
    result = qa.run(query)
    print(result)
    return {"result": result, "status": 200}

    # tools = [
    #     Tool(
    #         name='Knowledge Base',
    #         func=qa.run,
    #         description=(
    #             'use this tool when answering general knowledge queries to get '
    #             'more information about the topic'
    #         )
    #     )
    # ]
    #
    # agent = initialize_agent(
    #     agent='chat-conversational-react-description',
    #     tools=tools,
    #     llm=llm,
    #     verbose=True,
    #     max_iterations=3,
    #     early_stopping_method='generate',
    #     memory=conversational_memory
    # )
    #
    # result = agent(query)
    # #print(result)
    # return result

@app.post("/pinecone/upload/pdf")
async def create_upload_file(
        file: Annotated[UploadFile, File(description="A file read as UploadFile")],
        username: Annotated[str, Form()]
):
    print(username)
    print(file.filename)
    print(os.getcwd())

    try:
        pathlib.Path(f"{os.getcwd()}{DESTINATION}").mkdir(parents=True, exist_ok=True)
    except OSError:
        print("Create folder %s error" % f"{os.getcwd()}{DESTINATION}")
        return {"filename": file.filename}

    upload_path = os.path.join(f"{os.getcwd()}{DESTINATION}", file.filename)
    fileName = file.filename
    print({"info": f"file '{fileName}' saving to '{upload_path}'"})
    with open(upload_path, "wb+") as file_object:
        file_object.write(file.file.read())

    return {"filename": file.filename}


def getAndCreateIndex(indexName:str, apiKey:str, environment:str, metric:str):

    # for now always delete the index
    #if indexName in pinecone.list_indexes():
    #    pinecone.delete_index(indexName)
    # print("Using index %s " % f"{indexName}")
    # print("Using apiKey %s " % f"{apiKey}")
    # print("Using environment %s " % f"{environment}")
    # print("Using metric %s " % f"{metric}")

    pinecone.init(
        api_key=apiKey,  # find at app.pinecone.io
        environment=environment # next to api key in console
    )

    if indexName not in pinecone.list_indexes():
        pinecone.create_index(
            name=indexName,
            dimension=384,
            metric=metric
        )

    # now connect to the index
    #return pinecone.GRPCIndex(indexName)
    #
    return pinecone.Index(indexName)

# def getModel(modelname):
#     if 'all-MiniLM-L6-v2' == modelname:
#         device = 'cuda' if torch.cuda.is_available() else 'cpu'
#         if device != 'cuda':
#             print(f"You are using {device}. This is much slower than using "
#                   "a CUDA-enabled GPU. If on Colab you can change this by "
#                   "clicking Runtime > Change runtime type > GPU.")
#         return SentenceTransformer(modelname, device=device)
#     elif 'average_word_embeddings_komninos' == modelname:
#         device = 'cuda' if torch.cuda.is_available() else 'cpu'
#         return SentenceTransformer(modelname, device=device)
#     elif 'multi-qa-MiniLM-L6-cos-v1' == modelname:
#         device = 'cuda' if torch.cuda.is_available() else 'cpu'
#         # load the retriever model from huggingface model hub
#         return SentenceTransformer(modelname, device=device)
#     elif 'bert-base-nli-mean-tokens' == modelname:
#         return SentenceTransformer('sentence-transformers/bert-base-nli-mean-tokens')
#     elif 'all_datasets_v3_mpnet-base' == modelname:
#         return SentenceTransformer('flax-sentence-embeddings/all_datasets_v3_mpnet-base')
#     elif 'paraphrase-MiniLM-L6-v2' == modelname:
#         return SentenceTransformer(modelname)
#     elif 'all-mpnet-base-v2' == modelname:
#         return SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
#     elif 'average_word_embeddings_glove.6B.300d' == modelname:
#         return SentenceTransformer(modelname)
#     else:
#         raise Exception("Unknown model: " + modelname)