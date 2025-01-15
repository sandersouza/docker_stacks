![AICHAOS](images/banner.png)
# TSDB Exporter
Grafana K6, JMeter, LoadRunner, Locust, and others... at this moment doesn't support HTTP3/QUIC. This is a problem for me actualitty, because all my new applications take improvements on simutaneous multiples connections speed, security, keepalive connections, handshake in TCP, data throughtput in UDP with fallback solution in case of losse packets. Taking best of 2 worlds, completely tranparent for user... Old fashionist TCP and the new all Mighty Powerfull Google Creation QUIC can ! ( See RFC 9000, 9001 and 9369 ).

They coexist in perfect harmony, even using the same TCP port to initiate the connection, detecting which protocol the client supports and switching to it. This is perfect for slow and high-latency connections, as QUIC only sends headers when connecting and occasionally to check the connection's health. It operates across layers 3, 4, and 7 of the OSI model, with its own intelligence to handle issues effectively. See above:

The **QUIC** (Quick UDP Internet Connections) protocol interacts with the following OSI layers:

### **1. Layer 4: Transport**
- QUIC primarily operates at the **transport layer**, replacing **TCP**. It uses **UDP** as its foundation while adding advanced transport features such as:
  - Multiplexing of streams.
  - Built-in congestion control.
  - Efficient loss detection and retransmission mechanisms.

### **2. Layer 7: Application**
- QUIC incorporates functionalities that traditionally belong to either the transport or application layer, including:
  - Secure connection establishment (built-in TLS 1.3).
  - Stream and connection management within a single UDP connection.
  - Protocol design optimized for reducing latency in web applications, such as HTTP/3.

### **3. Layer 3: Network (Indirectly)*
- While QUIC does not directly operate at the network layer, it interacts with it through its use of **UDP**. This means it relies on Layer 3 functionalities, such as:
  - IP address management.
  - Packet routing between hosts.

### **Summary**:
**QUIC** primarily functions at **Layer 4 (Transport)** and **Layer 7 (Application)**, while indirectly interacting with **Layer 3 (Network)** due to its dependency on UDP. It's a groundbreaking protocol that combines intelligence and features from multiple layers to optimize performance and reduce latency.


## QUIC Protocol Overview ( from [RFC9000](https://datatracker.ietf.org/doc/rfc9000/) )

QUIC is a secure general-purpose transport protocol.  This document defines version 1 of QUIC, which conforms to the version-independent properties of QUIC defined in [QUIC-INVARIANTS]. QUIC is a connection-oriented protocol that creates a statefulinteraction between a client and server. The QUIC handshake combines negotiation of cryptographic and transport parameters.  QUIC integrates the TLS handshake [TLS13], although using a customized framing for protecting packets.  The integration of TLS and QUIC is described in more detail in
[QUIC-TLS].  The handshake is structured to permit the exchange of application data as soon as possible.  This includes an option for clients to send data immediately (0-RTT), which requires some form of
prior communication or configuration to enable. 

Endpoints communicate in QUIC by exchanging QUIC packets.  Most packets contain frames, which carry control information and application data between endpoints.  QUIC authenticates the entirety of each packet and encrypts as much of each packet as is practical. QUIC packets are carried in UDP datagrams [UDP] to better facilitate
deployment in existing systems and networks.

Application protocols exchange information over a QUIC connection via streams, which are ordered sequences of bytes.  Two types of streams can be created: bidirectional streams, which allow both endpoints to
send data; and unidirectional streams, which allow a single endpoint to send data.  A credit-based scheme is used to limit stream creation and to bound the amount of data that can be sent.

QUIC provides the necessary feedback to implement reliable delivery and congestion control.  An algorithm for detecting and recovering from loss of data is described in Section 6 of [QUIC-RECOVERY].  QUIC depends on congestion control to avoid network congestion.  An exemplary congestion control algorithm is described in Section 7 of [QUIC-RECOVERY].

QUIC connections are not strictly bound to a single network path. Connection migration uses connection identifiers to allow connections to transfer to a new network path.  Only clients are able to migrate
in this version of QUIC.  This design also allows connections to continue after changes in network topology or address mappings, such as might be caused by NAT rebinding.

Once established, multiple options are provided for connection termination.  Applications can manage a graceful shutdown, endpoints can negotiate a timeout period, errors can cause immediate connection
teardown, and a stateless mechanism provides for termination of connections after one endpoint has lost state.

## Usage example
> Simple usage, only one query with a label
```shell
$ curl -s -k -o /dev/null -X GET -H "Authorization: Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf" --write-out '%{json}' https://localhost:4433/quizzes/ | exporter.py --label curl-http
```

> With this, you can control the number of process to start ( Like VUsers)
```shell
$ while true; do seq 20 | xargs -P20 -I{} sh -c 'curl --http3 -s -k -o /dev/null -X GET -H "Authorization: Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf" --write-out "%{json}" https://localhost:4433/quizzes/ | ./exporter.py --label curl-quic' ; done
```