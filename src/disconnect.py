import socket

# List of IPs and ports used by Interactive Brokers
ib_ips_ports = [
    ("127.0.0.1", 4001),  # TWS Live
    ("127.0.0.1", 4002),  # TWS Paper
    ("127.0.0.1", 7497),  # TWS Paper
    ("127.0.0.1", 7496),  # TWS Live
    # Add more as needed
]

# Close the socket connections
for ip, port in ib_ips_ports:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        s.close()
        print(f"Connection closed for {ip}:{port}")
    except Exception as e:
        print(f"Failed to close connection for {ip}:{port}: {e}")
