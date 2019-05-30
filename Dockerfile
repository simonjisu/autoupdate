FROM ubuntu:18.04
LABEL maintainer "Simon Jang <simonjisu@gmail.com>"

ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN echo "XKBMODEL=\"pc105\"\n \
          XKBLAYOUT=\"us\"\n \
          XKBVARIANT=\"\"\n \
          XKBOPTIONS=\"\"" > /etc/default/keyboard
          
RUN apt-get update && apt-get install -y --no-install-recommends \
         build-essential \
         cmake \
         git \
         curl \
         vim \
         ca-certificates \
         libjpeg-dev \
         libpng-dev \
         sudo \
         apt-utils \
         man \
         tmux \
         less \
         wget \
         iputils-ping \
         zsh \
         htop \
         software-properties-common \
         tzdata \
         locales \
         openssh-server \
         xauth \
         rsync &&\
    rm -rf /var/lib/apt/lists/*
    
RUN locale-gen ko_KR.UTF-8
ENV LANG="ko_KR.UTF-8" LANGUAGE="ko_KR:en" LC_ALL="ko_KR.UTF-8"
RUN curl -o ~/miniconda.sh -O  https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh  && \
     chmod +x ~/miniconda.sh && \
     ~/miniconda.sh -b -p /opt/conda && \     
     rm ~/miniconda.sh
ENV PATH /opt/conda/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        libffi-dev \
        python-dev \
        python-pip \
        libsasl2-dev \
        libldap2-dev \
        python3.6-dev

RUN conda install python=3.6
RUN conda init zsh
RUN conda create -y -n venv python=3.6
RUN . activate venv
RUN pip install --upgrade setuptools pip
RUN pip install tqdm selenium bs4 superset pandas==0.23.4 sqlalchemy==1.2.18
RUN rm -rf ~/.cache/pip
ENV PYTHONUNBUFFERED=1
WORKDIR /root