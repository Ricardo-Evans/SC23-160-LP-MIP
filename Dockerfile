FROM gurobi/python:10.0.1_3.10
LABEL authors="SC23-160"

WORKDIR /SC23-160

ADD . .

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "dragonfly-model.py"]