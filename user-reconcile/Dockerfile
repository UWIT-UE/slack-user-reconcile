FROM gcr.io/google-appengine/python

RUN virtualenv /env -p python3.7

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD user-reconcile.py /app/user-reconcile.py

CMD [ "python", "/app/user-reconcile.py" ]
