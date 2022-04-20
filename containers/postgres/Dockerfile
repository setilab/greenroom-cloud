FROM postgres:13

COPY dict-american-english /usr/share/dict/words
RUN set -eux; \
    apt-get update && apt-get install -y \
      # For plpython3u extension, for generating test data
      python3 \
      python3-pip \
      postgresql-plpython3-$PG_MAJOR; \

# ENTRYPOINT and CMD will be inherited from postgres image
