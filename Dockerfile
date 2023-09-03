FROM jrottenberg/ffmpeg
# keep 3.9 as there are problems with pydantic
FROM python:3.9

# thats working but so it does not start the server
#RUN mkdir /home/soulsaver
#RUN chmod -R 777 /home/soulsaver
#RUN groupadd -r soulsaver && useradd -r -g soulsaver soulsaver
#USER soulsaver

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

#RUN apt install ffmpeg
#RUN apt-get install python3-bs4
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY ./main.py /code/

#
CMD ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "6081"]