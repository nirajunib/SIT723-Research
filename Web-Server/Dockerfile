# openssl version 3.0 or above
ARG OPENSSL_TAG=openssl-3.4.0

FROM ubuntu:latest
ARG OPENSSL_TAG

# install apache
RUN apt-get -y update && apt-get -y upgrade
RUN apt install -y apache2 
RUN apt install -y apache2-utils 

# enable ssl
WORKDIR /etc/ssl/
RUN openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 -subj \
    "/C=AU/ST=Victoria/L=Melbourne/O=Deakin/CN=localhost" \
    -keyout ./ssl.key -out ./ssl.crt
RUN cp ssl.key /etc/ssl/private/localhost.key
RUN cp ssl.crt /etc/ssl/certs/localhost.crt
RUN echo '<VirtualHost *:443>\n\
    DocumentRoot "/var/www/html"\n\
    ServerName localhost\n\
\n\
    SSLEngine on\n\
    SSLCertificateFile "/etc/ssl/certs/localhost.crt"\n\
    SSLCertificateKeyFile "/etc/ssl/private/localhost.key"\n\
</VirtualHost>' >> /etc/apache2/sites-available/localhost-ssl.conf
RUN echo 'ServerName localhost' >> /etc/apache2/apache2.conf

RUN a2enmod ssl &&\
    a2enmod rewrite &&\
    a2dissite 000-default default-ssl &&\
    a2ensite localhost-ssl

# install the OQS provider
RUN apt install -y git cmake libssl-dev openssl ninja-build

WORKDIR /opt
RUN git clone https://github.com/open-quantum-safe/oqs-provider.git
WORKDIR /opt/oqs-provider
RUN ./scripts/fullbuild.sh
RUN cmake --install _build
# run test to verify oqs-provider build
RUN ./scripts/runtests.sh
# add the provider
RUN echo '58a59,63\n\
> oqsprovider = oqsprovider_sect\n\
> [default_sect]\n\
> activate = 1\n\
> [oqsprovider_sect]\n\
> activate = 1\n\
71,72d75\n\
< [default_sect]\n\
< # activate = 1' > openssl.cnf.patch
RUN patch /etc/ssl/openssl.cnf openssl.cnf.patch
# list active OpenSSL providers
RUN openssl list -providers
# verify Quantum-safe algorithms are available
RUN openssl list -kem-algorithms -provider oqsprovider | egrep -i "(kyber|kem)768"
# setup apache with oqs
RUN echo '\nSSLOpenSSLConfCmd Curves X25519MLKEM768:X448:X25519:prime256v1' >> /etc/apache2/mods-enabled/ssl.conf

# expose port
EXPOSE 443

# run apache2
CMD ["apachectl", "-D", "FOREGROUND"]
