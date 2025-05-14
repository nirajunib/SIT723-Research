package main

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/binary"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"math/big"
	"os"
	"time"

	"github.com/cloudflare/circl/sign"
	"github.com/cloudflare/circl/sign/mldsa/mldsa44"
	"github.com/quic-go/quic-go"
)

var (
	mode       = flag.String("mode", "", "server or client")
	protocol   = flag.String("protocol", "tcp", "tcp or quic")
	addr       = flag.String("addr", "localhost:4444", "address to bind/connect")
	chunkSize  = flag.Int("chunk-size", 64*1024, "chunk size in bytes")
	size       = flag.Int("size", 1024*1024, "data size to send (client only)")
)

var (
	clientPrivateKey *rsa.PrivateKey
	clientCert       tls.Certificate

	scheme           = mldsa44.Scheme()
	clientMLPrivate  sign.PrivateKey
	clientMLPublic   sign.PublicKey
)

func initMLDSAKeys(privPath, pubPath string) (sign.PrivateKey, sign.PublicKey, error) {
	// Try to load existing keys
	privBytes, privErr := os.ReadFile(privPath)
	pubBytes, pubErr := os.ReadFile(pubPath)

	if privErr == nil && pubErr == nil {
		// Initialize the private and public key objects
		priv := new(mldsa44.PrivateKey)
		pub := new(mldsa44.PublicKey)

		// Unmarshal the private and public key data
		if err := priv.UnmarshalBinary(privBytes); err != nil {
			return nil, nil, fmt.Errorf("invalid private key: %w", err)
		}
		if err := pub.UnmarshalBinary(pubBytes); err != nil {
			return nil, nil, fmt.Errorf("invalid public key: %w", err)
		}

		// Ensure the keys are bound to the correct scheme
		pub.Scheme()  // Bind public key to its scheme
		priv.Scheme() // Bind private key to its scheme

		// Return the loaded keys
		return priv, pub, nil
	}

	// If keys don't exist, generate new ones
	pub, priv, err := mldsa44.GenerateKey(rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("key generation failed: %w", err)
	}

	// Save the new keys to the specified paths
	if err := os.WriteFile(privPath, priv.Bytes(), 0600); err != nil {
		return nil, nil, fmt.Errorf("failed to write private key: %w", err)
	}
	if err := os.WriteFile(pubPath, pub.Bytes(), 0644); err != nil {
		return nil, nil, fmt.Errorf("failed to write public key: %w", err)
	}

	// Ensure the keys are bound to the correct scheme after generation
	pub.Scheme()  // Bind public key to its scheme
	priv.Scheme() // Bind private key to its scheme

	// Return the generated keys
	return priv, pub, nil
}




func main() {
	flag.Parse()
	if *mode != "server" && *mode != "client" {
		log.Fatal("Mode must be 'server' or 'client'")
	}
	if err := ensureCertificates(); err != nil {
		log.Fatalf("Certificate generation error: %v", err)
	}


	var err error
		clientMLPrivate, clientMLPublic, err = initMLDSAKeys("client_mldsa_priv.key", "client_mldsa_pub.key")
		if err != nil {
			log.Fatalf("ML-DSA key init failed: %v", err)
		}
	// if *mode == "client" {
	// 	// var err error
	// 	// clientMLPublic, clientMLPrivate, err = mldsa44.GenerateKey(rand.Reader)
	// 	// initMLDSAKeys("ml_private.key", "ml_public.key")
	// 	// if err != nil {
	// 	// 	log.Fatalf("Failed to generate ML-DSA key: %v", err)
	// 	// }
	// 	var err error
	// 	clientMLPrivate, clientMLPublic, err = initMLDSAKeys("client_mldsa_priv.key", "client_mldsa_pub.key")
	// 	if err != nil {
	// 		log.Fatalf("ML-DSA key init failed: %v", err)
	// 	}

	// }
	tlsConfig := loadTLSConfig()
	if *mode == "server" {
		runServer(tlsConfig)
	} else {
		runClient(tlsConfig)
	}
}

func ensureCertificates() error {
	if _, err := os.Stat("ca.pem"); errors.Is(err, os.ErrNotExist) {
		return generateCertificates()
	}
	return nil
}

func generateCertificates() error {
	log.Println("Generating TLS certificates...")

	caKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	caTemplate := x509.Certificate{
		SerialNumber:          big.NewInt(2025),
		Subject:               pkix.Name{Organization: []string{"My CA"}},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(10 * 365 * 24 * time.Hour),
		IsCA:                  true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
	}
	caCertDER, _ := x509.CreateCertificate(rand.Reader, &caTemplate, &caTemplate, &caKey.PublicKey, caKey)
	writePem("ca.pem", "CERTIFICATE", caCertDER)
	writePem("ca-key.pem", "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(caKey))

	serverKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	serverTemplate := x509.Certificate{
		SerialNumber: big.NewInt(2026),
		Subject:      pkix.Name{CommonName: "localhost"},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:     x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}
	caCert, _ := x509.ParseCertificate(caCertDER)
	serverCertDER, _ := x509.CreateCertificate(rand.Reader, &serverTemplate, caCert, &serverKey.PublicKey, caKey)
	writePem("server.pem", "CERTIFICATE", serverCertDER)
	writePem("server-key.pem", "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(serverKey))

	clientKey, _ := rsa.GenerateKey(rand.Reader, 2048)
	clientTemplate := x509.Certificate{
		SerialNumber: big.NewInt(2027),
		Subject:      pkix.Name{CommonName: "client"},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
	}
	clientCertDER, _ := x509.CreateCertificate(rand.Reader, &clientTemplate, caCert, &clientKey.PublicKey, caKey)
	writePem("client.pem", "CERTIFICATE", clientCertDER)
	writePem("client-key.pem", "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(clientKey))

	log.Println("Certificates generated successfully.")
	return nil
}

func writePem(filename, blockType string, bytes []byte) {
	f, _ := os.Create(filename)
	defer f.Close()
	pem.Encode(f, &pem.Block{Type: blockType, Bytes: bytes})
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
	clientCert = cert
	clientPrivateKey = cert.PrivateKey.(*rsa.PrivateKey)

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
	} else {
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

func handleTCPConnection(conn *tls.Conn) {
	defer conn.Close()
	if err := conn.Handshake(); err != nil {
		log.Println("TLS handshake error:", err)
		return
	}
	handleConnWithVerify(conn)
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

func handleConnWithVerify(rw io.ReadWriter) {
	log.Println("🔌 Connection handler entered")

	var dataLen uint32
	if err := binary.Read(rw, binary.BigEndian, &dataLen); err != nil {
		log.Println("❌ Failed to read data length:", err)
		return
	}
	log.Println("📏 Declared data length:", dataLen)

	data, err := readFullInChunks(rw, int(dataLen))
	if err != nil {
		log.Printf("❌ Failed to read full data (%d/%d): %v", len(data), dataLen, err)
		return
	}
	log.Printf("📦 Received %d bytes of data", len(data))

	var sigLen uint32
	if err := binary.Read(rw, binary.BigEndian, &sigLen); err != nil {
		log.Println("❌ Failed to read signature length:", err)
		return
	}
	log.Println("🔐 Declared signature length:", sigLen)

	signature, err := readFullInChunks(rw, int(sigLen))
	if err != nil {
		log.Printf("❌ Failed to read full signature (%d/%d): %v", len(signature), sigLen, err)
		return
	}
	log.Printf("📝 Received %d bytes of signature", len(signature))

	// Verify signature
	if ok := clientMLPublic.Scheme().Verify(clientMLPublic, data, signature, nil); !ok {
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
	sig, err := clientMLPrivate.Sign(rand.Reader, data, crypto.Hash(0))
	if err != nil {
		log.Fatal("Private signature:", err)
	}

	if *protocol == "tcp" {
		conn, err := tls.Dial("tcp", *addr, tlsConfig)
		if err != nil {
			log.Fatal("Dial error:", err)
		}
		sendSignedData(conn, data, sig)
	} else {
		sess, err := quic.DialAddr(context.Background(), *addr, tlsConfig, nil)
		if err != nil {
			log.Fatal("QUIC dial error:", err)
		}
		stream, err := sess.OpenStreamSync(context.Background())
		if err != nil {
			log.Fatal("Open stream error:", err)
		}
		sendSignedData(stream, data, sig)
	}
}

func sendSignedData(w io.Writer, data []byte, sig []byte) {
	start := time.Now()

	// Send data length
	if err := binary.Write(w, binary.BigEndian, uint32(len(data))); err != nil {
		log.Println("❌ Failed to write data length:", err)
		return
	}

	// Send data in chunks
	for offset := 0; offset < len(data); {
		end := offset + *chunkSize
		if end > len(data) {
			end = len(data)
		}
		n, err := w.Write(data[offset:end])
		if err != nil {
			log.Printf("❌ Chunk write failed at %d-%d: %v", offset, end, err)
			return
		}
		offset += n
	}

	// Send signature length
	if err := binary.Write(w, binary.BigEndian, uint32(len(sig))); err != nil {
		log.Println("❌ Failed to write signature length:", err)
		return
	}

	// Send signature
	if _, err := w.Write(sig); err != nil {
		log.Println("❌ Failed to write signature:", err)
		return
	}

	// Flush for QUIC
	if flusher, ok := w.(interface{ Flush() error }); ok {
		if err := flusher.Flush(); err != nil {
			log.Println("❌ Flush failed:", err)
		}
	}

	// Delay before close for QUIC
	if stream, ok := w.(quic.Stream); ok {
		_ = stream.SetWriteDeadline(time.Now().Add(500 * time.Millisecond)) // allow time to flush
	}

	// Explicit Close
	if closer, ok := w.(io.Closer); ok {
		log.Println("🚪 Closing writer after sending")
		time.Sleep(1000 * time.Millisecond) // Give time for flush
		_ = closer.Close()
	}

	elapsed := time.Since(start).Seconds()
	log.Printf("✅ Sent %d bytes + %dB signature in %.2fs (%.2f MB/s)", len(data), len(sig), elapsed, float64(len(data))/(1024*1024)/elapsed)
}


func readFullInChunks(r io.Reader, totalLen int) ([]byte, error) {
	buf := make([]byte, 0, totalLen)
	chunk := make([]byte, 64*1024)
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
