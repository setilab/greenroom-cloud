FROM python:3.7
ENV PATH=/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin
RUN pip3 install cherrypy routes wsaccel ws4py redis
RUN useradd -ms /bin/bash api
USER api
WORKDIR /api
COPY *.py /api/
CMD ["python", "-u", "app.py"]
