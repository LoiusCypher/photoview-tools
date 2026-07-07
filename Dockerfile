ARG BASE=openeuler/openeuler:24.03-lts-sp1
FROM ${BASE} AS retinarcnn
#ARG VERSION=2.20.0

RUN dnf update -y \
    && dnf install -y python3-pip \
    && dnf install -y libxcb libGL \
    && dnf install -y git \
    && dnf install -y mariadb-connector-c-devel gcc python3-devel \
    && dnf install -y mariadb mysql-selinux \
    && dnf clean all \
    && rm -rf /tmp/* \
    && rm -rf /var/cache/dnf \
    && echo Done

RUN git clone https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0.git /Mask-RCNN_model
RUN sed -i -e "s:np\.bool:bool:g" /Mask-RCNN_model/mrcnn/utils.py
COPY app /app
WORKDIR /app
RUN pip3 install -r requirements.txt

