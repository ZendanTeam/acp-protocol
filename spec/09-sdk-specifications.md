# ACP Official SDK Architecture & Specifications (14 Languages)
**Document Number:** RFC-ACP-009  
**Version:** 1.0.0  

---

## 1. Universal SDK Architectural Principles

To ensure consistency, cross-language interoperability, and developer familiarity across the entire ecosystem, every official **ACP SDK** across all 14 supported languages adheres to four standardized core architectural layers:

```
+---------------------------------------------------------------------------------------------------+
|                                      ACP SDK HIGH-LEVEL ARCHITECTURE                              |
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  | LAYER 4: AGENT & WORKFLOW BUILDER API (Declarative Agent, Skill registration, DAG Builder)  |  |
|  +---------------------------------------------------------------------------------------------+  |
|  | LAYER 3: CORE CLIENT & CLIENT SESSION (Capability Token management, Replay check, Tracing)  |  |
|  +---------------------------------------------------------------------------------------------+  |
|  | LAYER 2: PROTOCOL ENVELOPE & SECURITY ENGINE (Canonicalization, Ed25519/ECDSA Signing/Verify)|  |
|  +---------------------------------------------------------------------------------------------+  |
|  | LAYER 1: TRANSPORT ADAPTERS (HTTP2, gRPC, WebSocket, Unix Socket, QUIC, P2P Mesh drivers)   |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Language-Specific Specifications & API Signatures

### 2.1 Python (`acp-python`)
- **Idioms:** Type annotations (`pydantic`), asynchronous execution (`asyncio`), and generator streaming (`AsyncIterator`).
```python
from acp import ACPClient, AgentManifest, Envelope, FrameType, Skill
from typing import AsyncIterator

async def run_agent():
    client = await ACPClient.connect("https://gateway.acp.local", did="did:acp:org:py-worker")
    
    @client.skill(name="optimize_sql", cost_credits=2.0)
    async def optimize_sql(query: str) -> str:
        return f"OPTIMIZED: {query}"
    
    # Asynchronous Streaming Call to Peer Agent
    async for chunk in client.stream(target_did="did:acp:org:db-agent", action="query", params={"sql": "SELECT *"}):
        print("Received chunk:", chunk.data)
```

### 2.2 TypeScript & JavaScript (`@acp/sdk`)
- **Idioms:** Strict TypeScript definitions (`Zod` schema inference), Promises, and `AsyncIterable` streams. Works natively in Node.js, Deno, Bun, and browser Web Workers.
```typescript
import { ACPClient, Envelope, FrameType } from "@acp/sdk";

const client = await ACPClient.connect({
  endpoint: "wss://gateway.acp.local/ws",
  did: "did:acp:org:ts-agent",
  privateKey: process.env.ACP_PRIVATE_KEY!
});

client.registerSkill("summarize_text", async (params: { text: string }) => {
  return { summary: params.text.slice(0, 100) };
});

for await (const chunk of client.streamRequest("did:acp:org:llm", "generate", { prompt: "Hello ACP" })) {
  process.stdout.write(chunk.data);
}
```

### 2.3 Go (`github.com/acp-protocol/acp-go`)
- **Idioms:** Goroutines, explicit error handling (`(Result, error)`), interfaces, and context cancellation (`context.Context`).
```go
package main

import (
	"context"
	"fmt"
	"github.com/acp-protocol/acp-go/acp"
)

func main() {
	ctx := context.Background()
	client, err := acp.Connect(ctx, "grpc://gateway.acp.local:50051", acp.WithDID("did:acp:org:go-agent"))
	if err != nil { panic(err) }
	defer client.Close()

	client.RegisterSkill("process_batch", func(ctx context.Context, req *acp.Request) (*acp.Response, error) {
		return acp.NewResponse(req, acp.StatusOK, map[string]interface{}{"processed": true}), nil
	})

	stream, _ := client.Stream(ctx, "did:acp:org:logger", "append_log", map[string]string{"msg": "started"})
	for stream.Next() {
		fmt.Println("Chunk:", stream.Chunk().Data)
	}
}
```

### 2.4 Rust (`acp-rs`)
- **Idioms:** Zero-copy deserialization (`serde`), memory safety (`Arc<TokioMutex>`), asynchronous futures (`tokio`), and strict compile-time type verification.
```rust
use acp_rs::{ACPClient, Config, Envelope, Result};
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<()> {
    let client = ACPClient::connect(Config::new("https://gateway.acp.local", "did:acp:org:rust-node")).await?;
    
    let mut stream = client.stream("did:acp:org:streamer", "start_stream", serde_json::json!({})).await?;
    while let Some(chunk) = stream.next().await {
        let frame = chunk?;
        println!("Chunk data: {:?}", frame.payload);
    }
    Ok(())
}
```

### 2.5 C# (`ACP.Net`)
- **Idioms:** `.NET 9` / `C# 13`, `async/await`, `IAsyncEnumerable<T>`, dependency injection (`IServiceCollection`), and `System.Text.Json`.
```csharp
using ACP.Net;
using ACP.Net.Models;

await using var client = await ACPClient.ConnectAsync("https://gateway.acp.local", "did:acp:org:csharp-worker");

client.RegisterSkill("CalculateRisk", async (Request req, CancellationToken ct) => {
    return new Response(Status.Success, new { riskScore = 0.04 });
});

await foreach (var chunk in client.StreamAsync("did:acp:org:market", "get_prices", new { symbol = "AAPL" })) {
    Console.WriteLine($"Price chunk: {chunk.Data}");
}
```

### 2.6 Java (`org.acp.sdk`)
- **Idioms:** Java 21+ Virtual Threads (`Project Loom`), `CompletableFuture`, Reactive Streams (`Flow.Publisher`), and Builder patterns.
```java
import org.acp.sdk.*;

public class ACPApplication {
    public static void main(String[] args) throws Exception {
        ACPClient client = ACPClient.builder()
            .endpoint("https://gateway.acp.local")
            .did("did:acp:org:java-worker")
            .buildAndConnect();

        client.registerSkill("processData", req -> 
            Response.success(req, Map.of("status", "processed"))
        );

        client.stream("did:acp:org:analytics", "report", Map.of())
            .forEach(chunk -> System.out.println("Chunk: " + chunk.getData()));
    }
}
```

### 2.7 Kotlin (`acp-kotlin`)
- **Idioms:** Kotlin Coroutines (`suspend`), `Flow<T>`, DSL builders, and null-safety.
```kotlin
import org.acp.sdk.kotlin.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

suspend fun main() = coroutineScope {
    val client = acpClient {
        endpoint = "https://gateway.acp.local"
        did = "did:acp:org:kotlin-agent"
    }

    client.skill("computeHash") { req ->
        Response.success(req, mapOf("hash" to req.params["input"]?.hashCode()))
    }

    client.stream("did:acp:org:target", "fetch", mapOf())
        .collect { chunk -> println("Received: ${chunk.data}") }
}
```

### 2.8 Swift (`ACPKit`)
- **Idioms:** Swift Concurrency (`async/await`, `AsyncSequence`, `Actor`), `Encodable/Decodable`, and strict memory management (`ARC`).
```swift
import ACPKit

@main
struct AgentRunner {
    static func main() async throws {
        let client = try await ACPClient.connect(to: "https://gateway.acp.local", did: "did:acp:org:swift-device")
        
        try await client.registerSkill("capturePhoto") { req in
            return Response.success(data: ["photoUrl": "file:///tmp/photo.jpg"])
        }
        
        for try await chunk in try await client.stream(target: "did:acp:org:cloud", action: "sync") {
            print("Received Swift Chunk: \(chunk.data)")
        }
    }
}
```

### 2.9 PHP (`acp/acp-php`)
- **Idioms:** PHP 8.3+, `Fibers` for non-blocking I/O (`Amphp/ReactPHP` compatibility), attributes (`#[AcpSkill]`), and PSR-18/PSR-7 bindings.
```php
<?php
use ACP\ACPClient;
use ACP\Attributes\AcpSkill;

$client = ACPClient::connect("https://gateway.acp.local", "did:acp:org:php-worker");

#[AcpSkill(name: "render_template")]
function renderTemplate(array $params): array {
    return ["html" => "<h1>Hello " . $params["name"] . "</h1>"];
}

$client->registerSkillFromCallable('renderTemplate');
$client->sendRequest("did:acp:org:router", "dispatch", ["data" => "test"]);
```

### 2.10 Ruby (`acp-ruby`)
- **Idioms:** Ruby 3.3+ `Ractors` / `Async` gem, idiomatic DSL blocks, and symbol hashes.
```ruby
require 'acp'

client = ACP::Client.connect("https://gateway.acp.local", did: "did:acp:org:ruby-agent")

client.skill("format_report") do |req|
  { status: "SUCCESS", formatted_text: req.params[:text].upcase }
end

client.stream("did:acp:org:collector", "ingest", { source: "ruby" }) do |chunk|
  puts "Chunk: #{chunk.data}"
end
```

### 2.11 Lua (`acp.lua`)
- **Idioms:** Table-driven metatables, coroutine yield/resume for asynchronous network loops, ideal for embedded game engines (`Defold/LÖVE`) and Nginx/OpenResty edge filters.
```lua
local acp = require("acp")

local client = acp.connect({
    endpoint = "http://gateway.acp.local",
    did = "did:acp:org:lua-agent"
})

client:register_skill("filter_packet", function(req)
    return { status = "SUCCESS", allowed = true }
end)

local stream = client:stream("did:acp:org:mesh", "monitor", {})
while stream:has_next() do
    local chunk = stream:next()
    print("Lua Chunk: " .. tostring(chunk.data))
end
```

### 2.12 C (`libacp`)
- **Idioms:** Pure C11 ABI, low-overhead struct pointers, explicit memory alloc/free (`acp_free_frame`), callback function pointers, and zero dependency on C++ runtimes (`POSIX` sockets).
```c
#include <acp/acp.h>
#include <stdio.h>

void on_chunk_received(const acp_frame_t* chunk, void* user_data) {
    printf("C Received Chunk sequence %d\n", chunk->sequence_number);
}

int main() {
    acp_client_t* client = acp_client_create("https://gateway.acp.local", "did:acp:org:c-embedded");
    acp_client_connect(client);
    
    acp_stream_options_t opts = { .on_chunk = on_chunk_received, .user_data = NULL };
    acp_client_stream(client, "did:acp:org:sensor", "read_all", "{}", &opts);
    
    acp_client_destroy(client);
    return 0;
}
```

### 2.13 C++ (`libacp-cpp`)
- **Idioms:** C++20/C++23 Coroutines (`co_await`), RAII (`std::unique_ptr`, `std::shared_ptr`), `std::expected` for error handling, and `std::span` for zero-copy binary streaming.
```cpp
#include <acp/client.hpp>
#include <iostream>

acp::Task<void> run_cpp_agent() {
    auto client = co_await acp::Client::connect("https://gateway.acp.local", "did:acp:org:cpp-node");
    
    client->register_skill("compute_matrix", [](const acp::Request& req) -> acp::Response {
        return acp::Response::success({{"determinant", 42.0}});
    });

    auto stream = co_await client->stream("did:acp:org:gpu", "execute_kernel", {{"kernel", "fft"}});
    while (auto chunk = co_await stream.next()) {
        std::cout << "C++ Chunk seq: " << chunk->sequence_number << std::endl;
    }
}
```
