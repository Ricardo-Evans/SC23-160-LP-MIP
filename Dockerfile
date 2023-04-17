FROM gurobi/python:latest
LABEL authors="SC23-160"

WORKDIR /SC23-160

ADD . .

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "dragonfly-model.py"]