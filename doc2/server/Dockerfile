FROM python:latest
WORKDIR /
COPY requirements.txt /
RUN pip install -r requirements.txt 
COPY test_kurs.py /
COPY test-kurs1-1aee0139edd0.json /
COPY k.txt /
ENTRYPOINT ["python"]
CMD ["test_kurs.py"]
