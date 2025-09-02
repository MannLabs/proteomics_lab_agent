# https://docs.streamlit.io/deploy/tutorials/docker
FROM python:3.12
# FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y

COPY ./requirements/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./proteomics_specialist ./proteomics_specialist

EXPOSE 8000

# HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["adk", "web", "--host=0.0.0.0"]
