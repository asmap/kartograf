# Container description file for running kartograf
# Example use:
#   podman build --tag kartograf .
#   mkdir -p data out
#   podman run --userns=keep-id -v $PWD/data:/data -v $PWD/out:/out kartograf 
FROM python:3.11
ARG RPKI_VERSION=9.6

# Download and install rpki-client from source
RUN set -x && \
  apt-get update && \
  apt-get -y install libtls-dev rsync && \
  wget "https://github.com/rpki-client/rpki-client-portable/releases/download/${RPKI_VERSION}/rpki-client-${RPKI_VERSION}.tar.gz" && \
  tar xfz "rpki-client-${RPKI_VERSION}.tar.gz" && \
  cd "rpki-client-${RPKI_VERSION}/"; \
  ./configure \
    --prefix=/usr \
    --with-user=rpki-client \
    --with-tal-dir=/etc/tals \
    --with-base-dir=/var/cache/rpki-client \
    --with-output-dir=/var/lib/rpki-client && \
  make V=1 && \
  addgroup --system --gid 900 rpki-client && \
  adduser --system --home /var/lib/rpki-client --gid 900 rpki-client && \
  make install

# Install kartograf's Python dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy over Python module
# We intentionally don't copy over `run` here, because the name "run" is created as a directory by podman.
COPY kartograf kartograf

# Define entry point
ENTRYPOINT ["python3", "-m", "kartograf.cli"]
