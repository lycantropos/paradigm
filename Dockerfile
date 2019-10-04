ARG PYTHON_IMAGE
ARG PYTHON_IMAGE_VERSION

FROM ${PYTHON_IMAGE}:${PYTHON_IMAGE_VERSION}

WORKDIR /opt/paradigm

COPY paradigm/ paradigm/
COPY tests/ tests/
COPY README.md .
COPY requirements.txt .
COPY requirements-tests.txt .
COPY setup.py .
COPY setup.cfg .

RUN pip install --force-reinstall -r requirements.txt
RUN pip install --force-reinstall -r requirements-tests.txt
