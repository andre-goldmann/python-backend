# Funktioniert mit lokalem start night
import os
import pathlib
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import pinecone
from decouple import config
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi import Form
from fastapi.middleware.cors import CORSMiddleware
from langchain import HuggingFaceHub, PromptTemplate
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Pinecone
from typing_extensions import Annotated
#from ctransformers.langchain import CTransformers
from pytube import YouTube
import os
import torch
import whisper
import pinecone
import numpy as np
import pandas as pd
from pytube import YouTube
import textwrap
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


prompt_template = """Answer the question based on the context below. If the
        question cannot be answered using the information provided answer
        with "I don't know".
        
        Context: {context}
        
        Question: {question}
        
        Answer: """

def setCustomPrompt():
    """
    Prompt template for QA
    """
    prompt = PromptTemplate(template=prompt_template, input_variables=['context', 'question'])
    return prompt

def load_llm():

    #compiler error
    #llm = CTransformers(model="llama-2-7b.ggmlv3.q2_K.bin", model_type="llama", max_new_tokens=512, temperature=0.5)
    #llm = CTransformers(model="meta-llama/Llama-2-7b-chat-hf", model_type="llama", max_new_tokens=512, temperature=0.5)
    # does not work
    #llm = AutoModelForCausalLM.from_pretrained('marella/gpt-2-ggml')

    return {}

def retrieval_qa_chain(llm, prompt, db):
    print("")
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=db.as_retriever(search_kwargs={'k': 1}),
        return_source_documents=True,
        chain_type_kwargs={'prompt':prompt}
    )
    return qa_chain

def qa_bot():
    print("Setting up bot")
    embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'})
    apiKey = config('PINECONE_API_KEY')
    indexName = config('PINECONE_INDEX')
    environment = config('PINECONE_ENVIRONMENT')

    pinecone.init(api_key=apiKey, environment=environment)
    db = Pinecone.from_existing_index(
        index_name=indexName,
        embedding=embeddings
    )
    llm = load_llm()
    qa_prompt = setCustomPrompt()
    qa = retrieval_qa_chain(llm, qa_prompt, db)
    return qa

def video_to_audio(video_url, destination):

    # Get the video
    video = YouTube(video_url)

    # Convert video to Audio
    audio = video.streams.filter(only_audio=True).first()

    # Save to destination
    output = audio.download(output_path = destination)

    name, ext = os.path.splitext(output)
    new_file = name + '.mp3'

    # Replace spaces with "_"
    new_file = new_file.replace(" ", "_")

    # Change the name of the file
    os.rename(output, new_file)

    return new_file

def audio_to_text(audio_file, whisper_model):
    return whisper_model.transcribe(audio_file)["text"]

@app.post("/pinecone/chatbotwithprompt", status_code=200)
async def chatbotwithprompt(
        query: Annotated[str, Form()]
):
    qa_result = qa_bot()
    response = qa_result({'query': query})
    print(response)
    return {"result": response, "status": 200}

#https://colab.research.google.com/github/pinecone-io/examples/blob/master/docs/langchain-retrieval-agent.ipynb#scrollTo=uITMZtzschJF

@app.post("/pinecone/youtubetotext", status_code=200)
async def youtubetotext(
        urls: Annotated[str, Form()]
):

    ################### YOUTUBE ####################
    list_videos = urls.split(",")#["https://www.youtube.com/watch?v=IdTMDpizis8"]
    print(list_videos)
    upload_path = os.path.join(f"{os.getcwd()}{DESTINATION}")
    # Create dataframe
    transcription_df = pd.DataFrame(list_videos, columns=['URLs'])
    transcription_df["file_name"] = transcription_df["URLs"].apply(lambda url: video_to_audio(url, upload_path))

    # Set the device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load the model
    whisper_model = whisper.load_model("large", device=device)
    print(upload_path + "Jocko_Willink_GOOD_(Official).mp3")

    # Apply the function to all the audio files
    transcription_df["transcriptions"] = transcription_df["file_name"].apply(lambda f_name: audio_to_text(f_name, whisper_model))

    wrapper = textwrap.TextWrapper(width=60)
    first_transcription = transcription_df.iloc[0]["transcriptions"]
    formatted_transcription = wrapper.fill(text=first_transcription)

    # Check first transcription
    print(formatted_transcription)
    ################### YOUTUBE ####################


@app.post("/pinecone/chatbot", status_code=200)
async def chatbot(
        query: Annotated[str, Form()]
):

    print("Start chat with %s " % f"{query}")
    apiKey = config('PINECONE_API_KEY')
    indexName = config('PINECONE_INDEX')
    environment = config('PINECONE_ENVIRONMENT')

    embeddings = HuggingFaceEmbeddings(
         model_name="all-MiniLM-L6-v2"
    )
    pinecone.init(api_key=apiKey, environment=environment)
    text_field = "content"

    vectorstore = Pinecone.from_existing_index(
        index_name=indexName,
        text_key=text_field,
        embedding=embeddings
    )

    llm=HuggingFaceHub(repo_id="bigscience/bloom", model_kwargs={"temperature":1e-10})
    #https://python.langchain.com/docs/integrations/llms/huggingface_hub
    #llm=HuggingFaceHub(repo_id="google/flan-t5-xl", model_kwargs={"temperature":1e-10})
    #llm=HuggingFaceHub(repo_id="google/flan-ul2", model_kwargs={"temperature":1e-10})
    #llm=HuggingFaceHub(repo_id="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={"temperature":1e-10})
    #llm=HuggingFaceHub(repo_id="Xenova/gpt-3.5-turbo", model_kwargs={"temperature":1e-10})

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )
    result = qa.run(query)
    print(result)

    return {"result": result, "status": 200}

    # conversational_memory = ConversationBufferWindowMemory(
    #     memory_key='chat_history',
    #     k=5,
    #     return_messages=True
    # )
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
    #     #agent='chat-conversational-react-description',
    #     agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    #     tools=tools,
    #     llm=llm,
    #     verbose=True,
    #     max_iterations=3,
    #     early_stopping_method='generate',
    #     memory=conversational_memory,
    #     handle_parsing_errors=True
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

@app.websocket("/backend/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")