package main

import (
	"crypto"
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"errors"
	"flag"
	"io"
	"log"
	"math/big"
	"os"
	"time"
	"encoding/binary"

	"github.com/quic-go/quic-go"
	mldsa "github.com/cloudflare/circl/sign/mldsa/mldsa44"
)

var (
	mode      = flag.String("mode", "", "server or client")
	protocol  = flag.String("protocol", "tcp", "tcp or quic")
	addr      = flag.String("addr", "localhost:4444", "address to bind/connect")
	chunkSize = flag.Int("chunk-size", 64*1024, "chunk size in bytes")
	size      = flag.Int("size", 1024*1024, "data size to send (client only)")
)


var mldsaContext = []byte("data-transfer") // shared context for ML-DSA


var (
	clientPrivateKey *mldsa.PrivateKey
	clientPublicKey  *mldsa.PublicKey
)

func main() {
	flag.Parse()
	if *mode != "server" && *mode != "client" {
		log.Fatal("Mode must be 'server' or 'client'")
	}
	if err := ensureCertificates(); err != nil {
		log.Fatalf("Certificate generation error: %v", err)
	}
	if err := ensureMLDSAKeys(); err != nil {
		log.Fatalf("ML-DSA key generation error: %v", err)
	}
	if err := loadMLDSAKeys(); err != nil {
		log.Fatalf("Failed to load ML-DSA keys: %v", err)
	}
	tlsConfig := loadTLSConfig()
	if *mode == "server" {
		runServer(tlsConfig)
	} else {
		runClient(tlsConfig)
	}
}

func writePemFile(filename, blockType string, data []byte) error {
	f, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer f.Close()
	return pem.Encode(f, &pem.Block{Type: blockType, Bytes: data})
}

func readPemFile(filename string) ([]byte, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(data)
	if block == nil {
		return nil, errors.New("invalid PEM file: " + filename)
	}
	return block.Bytes, nil
}

func ensureCertificates() error {
	if _, err := os.Stat("ca.pem"); errors.Is(err, os.ErrNotExist) {
		return generateCertificates()
	}
	return nil
}

func generateCertificates() error {
	log.Println("Generating RSA TLS certificates...")
	caKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	caTemplate := x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject:      pkix.Name{Organization: []string{"My CA"}},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(10 * 365 * 24 * time.Hour),
		IsCA:         true,
		KeyUsage:     x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
	}
	caCertDER, _ := x509.CreateCertificate(rand.Reader, &caTemplate, &caTemplate, &caKey.PublicKey, caKey)
	writePemFile("ca.pem", "CERTIFICATE", caCertDER)
	writePemFile("ca-key.pem", "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(caKey))

	serverKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	serverTemplate := x509.Certificate{
		SerialNumber: big.NewInt(2),
		Subject:      pkix.Name{CommonName: "localhost"},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:     x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}
	caCert, _ := x509.ParseCertificate(caCertDER)
	serverCertDER, _ := x509.CreateCertificate(rand.Reader, &serverTemplate, caCert, &serverKey.PublicKey, caKey)
	writePemFile("server.pem", "CERTIFICATE", serverCertDER)
	writePemFile("server-key.pem", "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(serverKey))

	clientKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	clientTemplate := x509.Certificate{
		SerialNumber: big.NewInt(3),
		Subject:      pkix.Name{CommonName: "client"},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
	}
	clientCertDER, _ := x509.CreateCertificate(rand.Reader, &clientTemplate, caCert, &clientKey.PublicKey, caKey)
	writePemFile("client.pem", "CERTIFICATE", clientCertDER)
	writePemFile("client-key.pem", "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(clientKey))
	log.Println("Certificates generated successfully.")
	return nil
}

func ensureMLDSAKeys() error {
	if _, err := os.Stat("mldsa-sk.pem"); errors.Is(err, os.ErrNotExist) {
		pk, sk, err := mldsa.GenerateKey(rand.Reader)
		if err != nil {
			return err
		}
		writePemFile("mldsa-sk.pem", "MLDSA PRIVATE KEY", sk.Bytes())
		writePemFile("mldsa-pk.pem", "MLDSA PUBLIC KEY", pk.Bytes())
	}
	return nil
}

func loadMLDSAKeys() error {
	skBytes, err := readPemFile("mldsa-sk.pem")
	if err != nil {
		return err
	}
	sk := new(mldsa.PrivateKey)
	if err := sk.UnmarshalBinary(skBytes); err != nil {
		return err
	}
	clientPrivateKey = sk

	pkBytes, err := readPemFile("mldsa-pk.pem")
	if err != nil {
		return err
	}
	pk := new(mldsa.PublicKey)
	if err := pk.UnmarshalBinary(pkBytes); err != nil {
		return err
	}
	clientPublicKey = pk
	return nil
}

func loadTLSConfig() *tls.Config {
	if *mode == "server" {
		cert, err := tls.LoadX509KeyPair("server.pem", "server-key.pem")
		if err != nil {
			log.Fatal("Server cert load error:", err)
		}
		caCert, _ := os.ReadFile("ca.pem")
		pool := x509.NewCertPool()
		pool.AppendCertsFromPEM(caCert)
		return &tls.Config{
			Certificates: []tls.Certificate{cert},
			ClientCAs:    pool,
			ClientAuth:   tls.RequireAndVerifyClientCert,
			NextProtos:   []string{"quic-test"},
		}
	}

	cert, err := tls.LoadX509KeyPair("client.pem", "client-key.pem")
	if err != nil {
		log.Fatal("Client cert load error:", err)
	}
	return &tls.Config{
		Certificates:       []tls.Certificate{cert},
		InsecureSkipVerify: true,
		NextProtos:         []string{"quic-test"},
	}
}

func runServer(tlsConfig *tls.Config) {
	if *protocol == "tcp" {
		ln, err := tls.Listen("tcp", *addr, tlsConfig)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("TCP TLS Server listening on", *addr)
		for {
			conn, err := ln.Accept()
			if err != nil {
				log.Println("Accept error:", err)
				continue
			}
			go handleTCPConnection(conn.(*tls.Conn))
		}
	} else if *protocol == "quic" {
		ln, err := quic.ListenAddr(*addr, tlsConfig, nil)
		if err != nil {
			log.Fatal(err)
		}
		log.Println("QUIC TLS Server listening on", *addr)
		for {
			sess, err := ln.Accept(context.Background())
			if err != nil {
				log.Println("QUIC accept error:", err)
				continue
			}
			go handleQUICSession(sess)
		}
	}
}

func handleQUICSession(sess quic.Connection) {
	for {
		stream, err := sess.AcceptStream(context.Background())
		if err != nil {
			log.Println("Error accepting QUIC stream:", err)
			return
		}
		go handleConnWithVerify(stream)
	}
}

func handleTCPConnection(conn *tls.Conn) {
	defer conn.Close()
	if err := conn.Handshake(); err != nil {
		log.Println("TLS handshake error:", err)
		return
	}
	handleConnWithVerify(conn)
}

func handleConnWithVerify(rw io.ReadWriter) {
	log.Println("🔌 Connection handler entered")

	var dataLen uint32
	if err := binary.Read(rw, binary.BigEndian, &dataLen); err != nil {
		log.Println("❌ Failed to read data length:", err)
		return
	}
	data, err := readFullInChunks(rw, int(dataLen))
	if err != nil {
		log.Printf("❌ Failed to read data: %v", err)
		return
	}

	var sigLen uint32
	if err := binary.Read(rw, binary.BigEndian, &sigLen); err != nil {
		log.Println("❌ Failed to read signature length:", err)
		return
	}
	signature, err := readFullInChunks(rw, int(sigLen))
	if err != nil {
		log.Printf("❌ Failed to read signature: %v", err)
		return
	}

	var pkLen uint32
	if err := binary.Read(rw, binary.BigEndian, &pkLen); err != nil {
		log.Println("❌ Failed to read public key length:", err)
		return
	}
	pkBytes := make([]byte, pkLen)
	if _, err := io.ReadFull(rw, pkBytes); err != nil {
		log.Println("❌ Failed to read public key:", err)
		return
	}
	pk := new(mldsa.PublicKey)
	if err := pk.UnmarshalBinary(pkBytes); err != nil {
		log.Println("❌ Invalid ML-DSA public key:", err)
		return
	}

	// if !mldsa.Verify(pk, []byte(""), data, signature) {
	if !mldsa.Verify(pk, mldsaContext, data, signature) {

		log.Println("❌ Signature verification failed")
	} else {
		log.Println("✅ Signature verified successfully")
		log.Printf("🔍 First 16 bytes of data: %x", data[:min(16, len(data))])
	}
}

func runClient(tlsConfig *tls.Config) {
	data := make([]byte, *size)
	for i := range data {
		data[i] = byte(i % 256)
	}
	// signature, err := clientPrivateKey.Sign(rand.Reader, data, crypto.Hash(0))
	signature, err := clientPrivateKey.Sign(rand.Reader, data, crypto.Hash(0))


	if err != nil {
		log.Fatal("Sign error:", err)
	}
	pkBytes := clientPublicKey.Bytes()

	if *protocol == "tcp" {
		conn, err := tls.Dial("tcp", *addr, tlsConfig)
		if err != nil {
			log.Fatal("Dial error:", err)
		}
		sendSignedData(conn, data, signature, pkBytes)
	} else {
		sess, err := quic.DialAddr(context.Background(), *addr, tlsConfig, nil)
		if err != nil {
			log.Fatal("QUIC dial error:", err)
		}
		stream, err := sess.OpenStreamSync(context.Background())
		if err != nil {
			log.Fatal("Open stream error:", err)
		}
		sendSignedData(stream, data, signature, pkBytes)
	}
}

func sendSignedData(w io.Writer, data, sig, pk []byte) {
	start := time.Now()
	binary.Write(w, binary.BigEndian, uint32(len(data)))
	w.Write(data)
	binary.Write(w, binary.BigEndian, uint32(len(sig)))
	w.Write(sig)
	binary.Write(w, binary.BigEndian, uint32(len(pk)))
	w.Write(pk)
	if closer, ok := w.(io.Closer); ok {
		closer.Close()
	}
	elapsed := time.Since(start).Seconds()
	log.Printf("✅ Sent %d bytes + %dB signature in %.2fs (%.2f MB/s)", len(data), len(sig), elapsed, float64(len(data))/(1024*1024)/elapsed)
}

func readFullInChunks(r io.Reader, totalLen int) ([]byte, error) {
	buf := make([]byte, 0, totalLen)
	chunk := make([]byte, *chunkSize)
	for len(buf) < totalLen {
		toRead := min(len(chunk), totalLen-len(buf))
		n, err := r.Read(chunk[:toRead])
		if n > 0 {
			buf = append(buf, chunk[:n]...)
		}
		if err != nil {
			return buf, err
		}
	}
	return buf, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
