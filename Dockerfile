ARG PYTHON_IMAGE
ARG PYTHON_IMAGE_VERSION

FROM ${PYTHON_IMAGE}:${PYTHON_IMAGE_VERSION}

WORKDIR /opt/paradigm

COPY requirements.txt .
RUN pip install --force-reinstall -r requirements.txt

COPY requirements-tests.txt .
RUN pip install --force-reinstall -r requirements-tests.txt

COPY README.md .
COPY setup.cfg .
COPY setup.py .
COPY paradigm/ paradigm/
COPY tests/ tests/
