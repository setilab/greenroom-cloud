FROM python:3.7
ENV PATH=/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin
RUN pip3 install redis
RUN useradd -ms /bin/bash event
USER event
WORKDIR /event
COPY *.py /event/
CMD ["python", "-u", "events.py"]
