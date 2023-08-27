# Funktioniert mit lokalem start night
# from src.dtos.ISayHelloDto import ISayHelloDto
import os
import pathlib

from fastapi import FastAPI, File, UploadFile
from fastapi import Form
from fastapi.middleware.cors import CORSMiddleware
from typing_extensions import Annotated

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
