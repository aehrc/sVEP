FROM --platform=x86_64 public.ecr.aws/lambda/provided:al2

# Install system packages and perl
RUN yum update -y && \
    yum install -y perl perl-App-cpanminus aws-cli gcc make perl-devel \
                   tar gzip \
                   openssl-devel \
                   libcurl-devel && \
    yum clean all

# Install perl packages
RUN cpanm --notest JSON Digest::MD5 IO::Socket::SSL Try::Tiny

ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy VEP files
COPY ./docker/VEP.pm ./docker/samtools ./docker/tabix ${LAMBDA_TASK_ROOT}/
COPY consequence ${LAMBDA_TASK_ROOT}/consequence
COPY lib ${LAMBDA_TASK_ROOT}/lib

# Make tabix and samtools executable
RUN chmod +x ${LAMBDA_TASK_ROOT}/samtools ${LAMBDA_TASK_ROOT}/tabix

# Copy lambda bootstrap and make executable
COPY ./docker/bootstrap /var/runtime/bootstrap
RUN chmod +x /var/runtime/bootstrap

# Set the PERL5LIB environment variable to include custom VEP lib directories
ENV PERL5LIB=${LAMBDA_TASK_ROOT}:${LAMBDA_TASK_ROOT}/consequence:${LAMBDA_TASK_ROOT}/lib:$PERL5LIB

# Set PATH to include custom VEP lib directory
ENV PATH=${LAMBDA_TASK_ROOT}/lib:${PATH}

# Define entry point
ENTRYPOINT ["/lambda-entrypoint.sh", "VEP::handle"]