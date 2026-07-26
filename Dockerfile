ARG BASE=openeuler/openeuler:latest # 24.03-lts-sp1
FROM ${BASE} AS retinarcnn
#ARG VERSION=2.20.0

RUN dnf update -y \
    && dnf install -y qt5-qtwayland xdg-utils dbus-x11  \
    && dnf install -y python3-pip \
    && dnf install -y libxcb libGL mesa-libGL-devel \
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
RUN pip3 install "labelme>=6.3.1" labelme2coco
#RUN pip3 install "labelme>=7.0.4" labelme2coco

ENV XDG_RUNTIME_DIR=/tmp/runtime-root
ENV XDG_SESSION_TYPE=wayland
ENV WAYLAND_DISPLAY=wayland-0
ENV QT_WAYLAND_SHELL_INTEGRATION=xdg-shell
ENV QT_QPA_PLATFORM=wayland

RUN mkdir -p $XDG_RUNTIME_DIR


