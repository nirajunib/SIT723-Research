## Dependencies

```bash
pip install cryptography aioquic
```

```bash
openssl req -new -x509 -keyout server.key -out server.crt -nodes -days 365
```


openssl x509 -in server.crt -out server.pem -outform PEM

openssl rsa -inform DER -in your.key -outform PEM -out key.pem
