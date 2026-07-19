ARG BASE=openeuler/openeuler:24.03-lts-sp1
FROM ${BASE} AS retinarcnn
#ARG VERSION=2.20.0

RUN dnf update -y \
    && dnf install -y pqtwayland5 xdg-utils dbus-x11 hatch \
    && dnf install -y python3-pip \
    && dnf install -y libxcb libGL \
    && dnf install -y git \
    && dnf install -y mariadb-connector-c-devel gcc python3-devel \
    && dnf install -y mariadb mysql-selinux \
    && dnf clean all \
    && rm -rf /tmp/* \
    && rm -rf /var/cache/dnf \
    && echo Done

RUN git clone https://github.com/LoiusCypher/Mask-RCNN_TF2.14.0.git /Mask-RCNN_model
RUN sed -i -e "s:np\.bool:bool:g" /Mask-RCNN_model/mrcnn/utils.py
COPY app /app
WORKDIR /app
RUN pip3 install -r requirements.txt

ENV WAYLAND_DISPLAY=wayland-0
ENV QT_WAYLAND_SHELL_INTEGRATION=xdg-shell
ENV QT_QPA_PLATFORM=wayland
ENV XDG_SESSION_TYPE=wayland
ENV XDG_RUNTIME_DIR=/tmp/Wayland-runtime-root
RUN mkdir -p $XDG_RUNTIME_DIR

ENTRYPOINT bash

