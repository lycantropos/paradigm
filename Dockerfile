ARG IMAGE_NAME
ARG IMAGE_VERSION

FROM ${IMAGE_NAME}:${IMAGE_VERSION}

WORKDIR /opt/paradigm

COPY pyproject.toml .
COPY README.md .
COPY setup.py .
COPY paradigm paradigm
COPY tests tests

RUN pip install -U pip
RUN pip install -e .[tests]
