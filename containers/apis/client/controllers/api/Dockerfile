FROM python:3.7
ENV PATH=/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin
RUN apt-get install libpq5
RUN pip3 install git+https://github.com/psycopg/psycopg.git#subdirectory=psycopg
RUN pip3 install redis cherrypy routes requests
RUN useradd -ms /bin/bash api
USER api
WORKDIR /api
COPY *.py /api/
CMD ["python", "-u", "app.py"]
