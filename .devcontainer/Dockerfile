FROM python:3.8-slim-bullseye

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install \
      git \
      curl \
      zip \
      unzip \
      groff \
      pass \
      make \
      pinentry-tty \
      vim \
      tox

RUN python3 -m ensurepip && \
        pip3 install --upgrade pip && \
        pip3 install pipenv

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip && ./aws/install
RUN rm awscliv2.zip

# AWS Vault
RUN curl -L -o /usr/local/bin/aws-vault https://github.com/99designs/aws-vault/releases/download/v6.6.1/aws-vault-linux-amd64
RUN chmod +x /usr/local/bin/aws-vault

# Terraform
RUN curl "https://releases.hashicorp.com/terraform/1.3.6/terraform_1.3.6_linux_amd64.zip" -o "terraform.zip"
RUN unzip -o terraform.zip -d /usr/local/bin
RUN chmod +x /usr/local/bin/terraform
RUN rm terraform.zip

# TFSec
RUN curl -L -o /usr/local/bin/tfsec https://github.com/aquasecurity/tfsec/releases/download/v1.28.1/tfsec-checkgen-linux-amd64
RUN chmod +x /usr/local/bin/tfsec

ARG USERNAME=awscommon
ARG USER_UID=1001
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --create-home --shell /bin/bash $USERNAME

# Command history
RUN mkdir /commandhistory
RUN touch /commandhistory/.bash_history
RUN chown -R ${USER_UID} /commandhistory
VOLUME /commandhistory

COPY bashrc /tmp
RUN cat /tmp/bashrc >> "/home/${USERNAME}/.bashrc"
RUN rm /tmp/bashrc
USER ${USERNAME}
