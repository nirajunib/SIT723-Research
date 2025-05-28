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
	"encoding/csv"
	"sync"
	"errors"
	"flag"
	"fmt"
	"io"
	"os/exec"
	"bytes"
	"path/filepath"
	"strings"
	"strconv"
	"regexp"
	"log"
	"math/big"
	"os"
	"time"

	"github.com/cloudflare/circl/sign"
	"github.com/cloudflare/circl/sign/mldsa/mldsa44"
	"github.com/quic-go/quic-go"
	"github.com/shirou/gopsutil/v3/cpu"
    "github.com/shirou/gopsutil/v3/mem"
)

var (
	mode       = flag.String("mode", "", "server or client")
	protocol   = flag.String("protocol", "tcp", "tcp or quic")
	addr       = flag.String("addr", "localhost:4444", "address to bind/connect")
	chunkSize  = flag.Int("chunk-size", 64*1024, "chunk size in bytes")
	size       = flag.Int("size", 1024*1024, "data size to send (client only)")
	enableMetrics = flag.Bool("metrics", false, "Enable metrics logging")
)



// LOGGING
type MetricsLogger struct {
    startTime     time.Time
    connStart     time.Time
    // handshakeTime time.Duration
    totalBytes    int64
    lock          sync.Mutex
    writer        *csv.Writer
    file          *os.File
    tickerStop    chan struct{}
}

func NewMetricsLogger() *MetricsLogger {
    logDir := fmt.Sprintf("logs/server/%s", *protocol)
	os.MkdirAll(logDir, os.ModePerm)
    filename := fmt.Sprintf("%s/metrics-%s.csv", logDir, time.Now().Format("20060102-150405"))
    file, err := os.Create(filename)
    if err != nil {
        log.Fatalf("Failed to create log file: %v", err)
    }

    writer := csv.NewWriter(file)
    writer.Write([]string{
        "Elapsed(ms)", "CPU(%)", "Memory(MB)", "Throughput(MB/s)", "ConnDuration(s)",
    })
    writer.Flush()

    return &MetricsLogger{
        startTime:     time.Now(),
        // handshakeTime: handshakeTime,
        writer:        writer,
        file:          file,
        tickerStop:    make(chan struct{}),
    }
}

func (m *MetricsLogger) Start(connStart time.Time) {
    log.Println("📈 MetricsLogger started")
    m.connStart = connStart

    go func() {
        ticker := time.NewTicker(100 * time.Millisecond)
        defer ticker.Stop()
        for {
            select {
            case <-m.tickerStop:
                return
            case now := <-ticker.C:
                m.lock.Lock()
                elapsed := now.Sub(m.startTime)
                connDuration := now.Sub(m.connStart)
                cpuPerc, _ := cpu.Percent(0, false)
                vm, _ := mem.VirtualMemory()

                // Convert throughput to Megabits per second
				throughputMB := float64(m.totalBytes) / 1_000_000.0 / elapsed.Seconds()

                m.writer.Write([]string{
                    fmt.Sprintf("%d", elapsed.Milliseconds()),
                    fmt.Sprintf("%.4f", cpuPerc[0]),
                    fmt.Sprintf("%.4f", float64(vm.Used)/1024.0/1024.0),
                    fmt.Sprintf("%.4f", throughputMB),
                    // fmt.Sprintf("%.2f", 0.0), // TODO: real packet loss
                    // fmt.Sprintf("%.4f", m.handshakeTime.Seconds()),
                    fmt.Sprintf("%.4f", connDuration.Seconds()),
                })
                m.writer.Flush()
                m.lock.Unlock()
            }
        }
    }()
}

func (m *MetricsLogger) AddBytes(n int) {
    m.lock.Lock()
    m.totalBytes += int64(n)
    m.lock.Unlock()
}

func (m *MetricsLogger) Stop() {
    close(m.tickerStop)

    m.lock.Lock()
    defer m.lock.Unlock()

    m.writer.Flush()
    m.file.Close()
    log.Println("🛑 MetricsLogger stopped and file closed.")
}


// CLIENT LOGGING


func getPingRTT(host string) (time.Duration, error) {
	// Run a single ICMP ping (Linux/macOS/WSL)
	cmd := exec.Command("ping", "-c", "1", host)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out

	if err := cmd.Run(); err != nil {
		return 0, err
	}

	// Extract time=XX ms using regex
	re := regexp.MustCompile(`time[=<]([\d.]+) ms`)
	matches := re.FindStringSubmatch(out.String())
	if len(matches) < 2 {
		return 0, fmt.Errorf("could not parse ping output: %s", out.String())
	}

	ms, err := strconv.ParseFloat(matches[1], 64)
	if err != nil {
		return 0, err
	}

	return time.Duration(ms * float64(time.Millisecond)), nil
}

func writeMetricsToCSV(handshake, latency, rtt, ttc time.Duration) {
	logDir := fmt.Sprintf("logs/client/%s", *protocol)
	os.MkdirAll(logDir, os.ModePerm)

	filename := fmt.Sprintf("metrics-%s.csv", time.Now().Format("20060102-150405"))
	filePath := filepath.Join(logDir, filename)

	newFile := false
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		newFile = true
	}

	file, err := os.OpenFile(filePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Println("Error opening CSV file:", err)
		return
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	if newFile {
		writer.Write([]string{"Handshake(ms)", "Latency(ms)", "RTT(ms)", "TTC(ms)"})
	}

	writer.Write([]string{
		formatDuration(handshake),
		formatDuration(latency),
		formatDuration(rtt),
		formatDuration(ttc),
	})
}

func formatDuration(d time.Duration) string {
	return fmt.Sprintf("%.3f", float64(d.Microseconds())/1000.0) // milliseconds with 3 decimal places
}

// LOGGING END



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
			// CurvePreferences left nil to enable X25519Kyber768 by default, run with GODEBUG=tlsmlkem=1 go run
			// https://tip.golang.org/doc/go1.24
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
			// CurvePreferences left nil to enable X25519Kyber768 by default, run with GODEBUG=tlsmlkem=1 go run
		// https://tip.golang.org/doc/go1.24
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
	// Start handshake measurement
    // handshakeStart := time.Now()
	

	defer conn.Close()
	if err := conn.Handshake(); err != nil {
		log.Println("TLS handshake error:", err)
		return
	}
	// state := conn.ConnectionState()
	// if len(state.PeerCertificates) == 0 {
	// 	log.Println("No client certificate found")
	// 	return
	// }

	if err := performMLDSAHandshake(conn, clientMLPrivate, clientMLPublic, true); err != nil {
		log.Println("ML-DSA handshake failed:", err)
		return
	}
	
	// End of handshake
    // handshakeTime := time.Since(handshakeStart)
	connStart := time.Now()
	var metrics *MetricsLogger
	if *enableMetrics {
		metrics = NewMetricsLogger()
		metrics.Start(connStart)
		defer func() {
			metrics.Stop()
		}()
	}

	handleConnWithVerify(conn, metrics) // only does the logic
	log.Println("🛑 TCP connection handler finished")
}


func handleQUICSession(sess quic.Connection) {

	for {
		stream, err := sess.AcceptStream(context.Background())
		if err != nil {
			log.Println("Error accepting QUIC stream:", err)
			return
		}
		go handleQuicStreamWithVerify(stream, sess)
	}
}

func handleQuicStreamWithVerify(stream quic.Stream, sess quic.Connection) {
	// Start handshake measurement
    // handshakeStart := time.Now()
	defer stream.Close()
	
	// state := sess.ConnectionState().TLS
	// if len(state.PeerCertificates) == 0 {
	// 	log.Println("No client certificate found")
	// 	return
	// }
	if err := performMLDSAHandshake(stream, clientMLPrivate, clientMLPublic, true); err != nil {
		log.Println("ML-DSA handshake failed:", err)
		return
	}
	

	// End of handshake
    // handshakeTime := time.Since(handshakeStart)
	connStart := time.Now()
	var metrics *MetricsLogger
	if *enableMetrics {
		metrics = NewMetricsLogger()
		metrics.Start(connStart)
		defer func() {
			metrics.Stop()
		}()
	}

	handleConnWithVerify(stream, metrics) // only does the logic
	log.Println("🛑 QUIC connection handler finished")
}

func handleConnWithVerify(rw io.ReadWriter, metrics *MetricsLogger) {
	log.Println("🔌 Connection handler entered")

	var dataLen uint32
	if err := binary.Read(rw, binary.BigEndian, &dataLen); err != nil {
		log.Println("❌ Failed to read data length:", err)
		return
	}
	log.Println("📏 Declared data length:", dataLen)

	data, err := readFullInChunksWithMetrics(rw, int(dataLen), metrics)
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

	signature, err := readFullInChunksWithMetrics(rw, int(sigLen), metrics)
	if err != nil {
		log.Printf("❌ Failed to read full signature (%d/%d): %v", len(signature), sigLen, err)
		return
	}
	log.Printf("📝 Received %d bytes of signature", len(signature))

	// Verify signature
	hstart := time.Now()
	if ok := clientMLPublic.Scheme().Verify(clientMLPublic, data, signature, nil); !ok {
		hstop := time.Since(hstart)
		log.Printf("⏱ Verification duration: %v", hstop)
		log.Println("❌ Signature verification failed")
	} else {
		hstop := time.Since(hstart)
		log.Printf("⏱ Verification duration: %v", hstop)
		log.Println("✅ Signature verified successfully")
		log.Printf("🔍 First 16 bytes of data: %x", data[:min(16, len(data))])
	}
}

func performMLDSAHandshake(rw io.ReadWriter, priv sign.PrivateKey, pub sign.PublicKey, isServer bool) error {
	challenge := make([]byte, 32)

	if isServer {
		// Receive challenge from client
		if _, err := io.ReadFull(rw, challenge); err != nil {
			return fmt.Errorf("server failed to read challenge: %w", err)
		}

		// Sign and send
		sig, err := priv.Sign(rand.Reader, challenge, nil)
		if err != nil {
			return fmt.Errorf("server sign failed: %w", err)
		}
		if err := binary.Write(rw, binary.BigEndian, uint32(len(sig))); err != nil {
			return fmt.Errorf("server failed to write sig length: %w", err)
		}
		_, err = rw.Write(sig)
		return err
	} else {
		// Generate and send challenge
		if _, err := rand.Read(challenge); err != nil {
			return fmt.Errorf("client failed to generate challenge: %w", err)
		}
		if _, err := rw.Write(challenge); err != nil {
			return fmt.Errorf("client failed to write challenge: %w", err)
		}

		// Receive and verify signature
		var sigLen uint32
		if err := binary.Read(rw, binary.BigEndian, &sigLen); err != nil {
			return fmt.Errorf("client failed to read sig length: %w", err)
		}
		sig := make([]byte, sigLen)
		if _, err := io.ReadFull(rw, sig); err != nil {
			return fmt.Errorf("client failed to read sig: %w", err)
		}
		if !pub.Scheme().Verify(pub, challenge, sig, nil) {
			return errors.New("client ML-DSA verification failed")
		}
		return nil
	}
}

func runClient(tlsConfig *tls.Config) {
	

	data := make([]byte, *size)
	for i := range data {
		data[i] = byte(i % 256)
	}
	start := time.Now()
	sig, err := clientMLPrivate.Sign(rand.Reader, data, crypto.Hash(0))
	if err != nil {
		log.Fatal("Private signature:", err)
	}

	var handshakeStart, handshakeEnd, sendEnd time.Time

	if *protocol == "tcp" {
		handshakeStart = time.Now()
		conn, err := tls.Dial("tcp", *addr, tlsConfig)
		handshakeEnd = time.Now()
		if err != nil {
			log.Fatal("Dial error:", err)
		}
		defer conn.Close()

		if err := performMLDSAHandshake(conn, nil, clientMLPublic, false); err != nil {
			log.Fatal("ML-DSA handshake failed:", err)
		}
		

		sendSignedData(conn, data, sig)
		sendEnd = time.Now()
	} else {
		handshakeStart = time.Now()
		sess, err := quic.DialAddr(context.Background(), *addr, tlsConfig, nil)
		handshakeEnd = time.Now()
		if err != nil {
			log.Fatal("QUIC dial error:", err)
		}
		stream, err := sess.OpenStreamSync(context.Background())
		if err != nil {
			log.Fatal("Open stream error:", err)
		}
		defer stream.Close()

		if err := performMLDSAHandshake(stream, nil, clientMLPublic, false); err != nil {
			log.Fatal("ML-DSA handshake failed:", err)
		}		

		sendSignedData(stream, data, sig)
		sendEnd = time.Now()
	}

	handshakeDuration := handshakeEnd.Sub(handshakeStart)
	ttc := sendEnd.Sub(start)

	// Get RTT via system ping
	host := strings.Split(*addr, ":")[0]
	rtt, err := getPingRTT(host)
	if err != nil {
		log.Println("Ping RTT error:", err)
		rtt = 0
	}
	latency := rtt / 2

	writeMetricsToCSV(handshakeDuration, latency, rtt, ttc)
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
		time.Sleep(500 * time.Millisecond) // Give time for flush
		_ = closer.Close()
	}

	elapsed := time.Since(start).Seconds()
	log.Printf("✅ Sent %d bytes + %dB signature in %.2fs (%.2f MB/s)", len(data), len(sig), elapsed, float64(len(data))/(1024*1024)/elapsed)
}


func readFullInChunksWithMetrics(r io.Reader, total int, metrics *MetricsLogger) ([]byte, error) {
    buf := make([]byte, total)
    var read int
    for read < total {
        n, err := r.Read(buf[read:])
        if n > 0 && metrics != nil {
            metrics.AddBytes(n)
        }
        if err != nil {
            return buf[:read], err
        }
        read += n
    }
    return buf, nil
}


func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}