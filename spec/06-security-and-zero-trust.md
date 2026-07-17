# ACP Enterprise Security & Zero-Trust Specification
**Document Number:** RFC-ACP-006  
**Version:** 1.0.0  

---

## 1. Zero-Trust Security Philosophy

The **Agent Collaboration Protocol (ACP)** enforces a strict **Zero-Trust Security Architecture (`ZTSA`)**: *Never trust, always verify, cryptographically prove identity and authorization on every single frame.*

In a distributed multi-agent mesh across public and hybrid clouds, network perimeters do not exist. An attacker who compromises one agent, host, or local network switch must not be able to forge messages, escalate privileges, query unauthorized memory, or command neighboring agents.

```
+---------------------------------------------------------------------------------------------------+
|                                 ACP ZERO-TRUST REQUEST LIFECYCLE                                  |
|                                                                                                   |
|  +--------------------+         1. Send Signed Envelope + CapabilityToken                         |
|  |     SENDING AGENT  | --------------------------------------------------------+                 |
|  | (did:acp:finance)  |                                                         |                 |
|  +--------------------+                                                         v                 |
|                                                                     +---------------------------+ |
|                                                                     |        ACP GATEWAY        | |
|                                                                     | (mTLS Termination & Proxy)| |
|                                                                     +---------------------------+ |
|                                                                                 |                 |
|        +------------------------------------------------------------------------+                 |
|        |                                                                                          |
|        v                                                                                          |
|  [ STEP 1: TLS 1.3 mTLS Verification ] ----> Verify Peer X.509 Certificate against Root CA        |
|        |                                                                                          |
|        v                                                                                          |
|  [ STEP 2: Replay Protection Check ]   ----> Verify (timestamp_ns, nonce) not in Eviction Cache   |
|        |                                                                                          |
|        v                                                                                          |
|  [ STEP 3: Cryptographic Signature ]   ----> Verify Ed25519/ECDSA signature using DID PubKey      |
|        |                                                                                          |
|        v                                                                                          |
|  [ STEP 4: Capability Token & ABAC ]   ----> Verify CapabilityToken claims, signatures & ABAC     |
|        |                                                                                          |
|        v                                                                                          |
|  [ STEP 5: Rate Limiting Enforcement ] ----> Check Token Bucket (Allow if credits > 0)            |
|        |                                                                                          |
|        +------------------------------------------------------------------------+                 |
|                                                                                 |                 |
|                                                                                 v                 |
|                                                                     +---------------------------+ |
|                                                                     |      RECEIVING AGENT      | |
|                                                                     |   (Sandboxed Execution)   | |
|                                                                     +---------------------------+ |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Authentication & Identity Management

### 2.1 Decentralized Identifiers (`DIDs`)
Every agent, host, and user in the ACP mesh is identified by a W3C-compliant Decentralized Identifier:
```
did:acp:<organization-hash>:<agent-unique-name>
Example: did:acp:7f8c9b2a:finance-auditor-v2
```
The public key and security metadata for every DID are published to the **ACP Registry** and cached by local Gateways.

### 2.2 OAuth 2.0 & OpenID Connect (`OIDC`) Federation
When human operators (`Agent -> Human`) or external enterprise applications connect to an ACP Gateway, authentication is handled via **OIDC and OAuth 2.0 Client Credentials Grant / Token Exchange (`RFC 8693`)**:
- The client exchanges its enterprise credentials with the **ACP Identity Provider (`IdP`)**.
- The IdP issues a **JSON Web Token (`JWT`)** bearing `sub: did:acp:...`, `iss: https://idp.acp.protocol.org`, `aud: acp-mesh`, and explicit role claims.
- This JWT is embedded within `security.auth_token` on all outbound envelopes.

### 2.3 Mutual TLS (`mTLS`) Transport Encryption
All Host-to-Host, Gateway-to-Router, and Router-to-Broker transport links enforce **TLS 1.3 or QUIC with Mutual X.509 Certificate Authentication (`mTLS`)**.
- Both client and server verify each other's certificates against an enterprise root Certificate Authority (`CA`) or ephemeral short-lived certificate authority (`SPIFFE/SPIRE` integration).
- Cipher suites are restricted to `TLS_AES_256_GCM_SHA384` and `TLS_CHACHA20_POLY1305_SHA256`. Legacy TLS 1.0/1.1/1.2 protocols and non-PFS (Perfect Forward Secrecy) ciphers are strictly prohibited.

---

## 3. Authorization & Access Control

### 3.1 Role-Based (`RBAC`) and Attribute-Based Access Control (`ABAC`)
While RBAC assigns broad static roles (`Admin`, `Worker`, `Viewer`), distributed multi-agent systems require granular dynamic rules. ACP enforces **ABAC** policies evaluated by Gateways and Gatekeepers:
- **Attributes Evaluated:** Subject DID, Target Resource URI, Requested Action (`READ`, `WRITE`, `EXECUTE`, `DELEGATE`), Current Time, Agent Sandboxing Tier, and Current Cost Budget.
- **Example ABAC Policy Rule:** *An agent with role `FinanceWorker` may `EXECUTE` the tool `sql_query` ONLY IF `abac_claims.environment == "staging"` AND `current_cost_credits < max_cost_credits`.*

### 3.2 Zero-Trust Capability Tokens (`capability-token.schema.json`)
To eliminate the risk of ambient privilege escalation, agents must obtain and present **Capability Tokens** to interact with specific resources or delegate tasks.
- A Capability Token is a cryptographically signed JSON object issued by an owner DID granting granular rights:
  ```json
  {
    "token_id": "cap_998877",
    "issuer_did": "did:acp:org:admin",
    "subject_did": "did:acp:org:worker-alpha",
    "issued_at_ns": 1784332800000000000,
    "expires_at_ns": 1784336400000000000,
    "capabilities": [
      {
        "resource": "memory://long-term/financial-records/*",
        "actions": ["READ"],
        "conditions": { "max_invocations": 50 }
      }
    ],
    "signature": "MEUCIQDx..."
  }
  ```
- Before any Memory Service read/write or Tool execution occurs, the target resource validates the Capability Token signature against `issuer_did`, checks that `current_time < expires_at_ns`, and increments the usage counter to enforce `max_invocations`.

---

## 4. Message Integrity, Confidentiality & Replay Protection

### 4.1 Signed Messages (`Ed25519` / `ECDSA`)
Every single frame transmitted over ACP must carry a valid cryptographic signature (`security.signature`) computed over the canonicalized envelope header and payload string. Any tampering by intermediate proxies or man-in-the-middle attackers immediately invalidates the signature, causing the frame to be dropped with an audit alert.

### 4.2 End-to-End Payload Encryption (`E2EE`)
When transmitting sensitive payloads through semi-trusted brokers or third-party routers, senders enable **End-to-End Encryption (`E2EE`)**:
- The sender generates a random 256-bit symmetric ephemeral key (`K_E`).
- The payload is encrypted using `AES-256-GCM` with a 96-bit random nonce (`IV`), producing `ciphertext` and `auth_tag`.
- The symmetric key `K_E` is encrypted against the receiver agent's public key using **HPKE (Hybrid Public Key Encryption `RFC 9180`)** and placed in `security.encrypted_key`.
- Intermediate routers can inspect routing headers and enforce rate limits while the payload body remains completely opaque and confidential (`ciphertext`). Only the target agent holding the private key corresponding to `receiver.target_id` can decrypt `encrypted_key` and access the plaintext payload.

### 4.3 Cryptographic Replay Protection
An attacker intercepting a valid, signed message (`e.g., "Transfer $1,000 to Account X"`) must not be able to replay that frame to trigger duplicate executions.
- Every envelope includes `timestamp_ns` and a cryptographically secure random `nonce` string.
- Gateways and Gatekeepers enforce a maximum time skew (`ttl_ms`, default 30 seconds). If `abs(current_time_ns - timestamp_ns) > (ttl_ms * 1,000,000)`, the frame is dropped immediately.
- For all valid frames falling within the `ttl_ms` window, Gateways maintain an in-memory **Nonce Eviction Cache** (`Bloom Filter` + `LRU Set`). If `nonce` is already present in the cache, the frame is rejected with `403 Forbidden - Replay Attack Detected`.

---

## 5. Runtime Isolation, Sandboxing & Rate Limiting

### 5.1 Agent Sandboxing & Session Isolation
Agents executing non-deterministic LLM output or arbitrary code plugins must be strictly isolated:
- **Process Tier:** Each agent runtime executes within an unprivileged Linux process under strict **POSIX cgroups v2** limits (`cpu.max`, `memory.max`) and **seccomp-bpf** system call filters (blocking `execve`, `ptrace`, `chroot`).
- **Container/Wasm Tier:** High-security agents run inside isolated **WebAssembly (`WASI`)** sandboxes or **Micro-VMs (`Firecracker`)** where file system access is strictly read-only except for ephemeral scratch directories tied to `correlation_id`.
- **Session Isolation:** Memory partitions, scratch files, and environment variables are completely isolated by session namespace (`partition_key = session_id`). When a session completes or times out, the Host immediately destroys the container and wipes all ephemeral scratch data (`Zero-out memory buffer`).

### 5.2 Secrets Vault
Agents never store API keys, database passwords, or private keys in plaintext manifests or memory.
- The **ACP Secrets Vault** securely stores credentials in encrypted enclaves (`AES-256-GCM`).
- When an agent makes an API or tool call requiring a secret (`e.g., Stripe API Key`), the agent sends the request with a placeholder `secrets://stripe/api_key`. The local ACP Gateway intercepts the request, verifies the agent's Capability Token against the Secrets Vault, injects the real API key into the outgoing HTTP header (`Authorization: Bearer <key>`), and forwards the request without ever exposing the raw secret to the agent's application memory or LLM context window.

### 5.3 Distributed Rate Limiting & Denial-of-Service (`DoS`) Protection
To prevent rogue or runaway agents from exhausting cluster compute or API budgets, Gateways enforce **Distributed Token Bucket Rate Limiting**:
- Every DID is assigned a rate limit profile (e.g., `1,000 frames/min` and `100 credits/min`).
- Gateways coordinate bucket levels via high-speed Redis counters or local memory token replenishment loops.
- If an agent exceeds its allowed token consumption rate, the Gateway rejects excess frames with HTTP/ACP status `429 Too Many Requests` and emits an `SLA_VIOLATION_RATE_LIMIT` security event to the Monitoring dashboard.

### 5.4 Immutable Cryptographic Audit Logs
Every authentication attempt, authorization failure, task delegation, capability grant, and security rejection is logged to the **ACP Logging Service**:
- Audit log records append the complete frame header, cryptographic signature, and decision result (`ALLOW` / `DENY`).
- Log files are written to **Write-Once-Read-Many (`WORM`)** storage using cryptographic hash chaining (`Hash(record_N) = SHA256( record_N + Hash(record_N-1) )`), guaranteeing that even a compromised system administrator cannot alter or delete historical audit trails without immediate detection.
