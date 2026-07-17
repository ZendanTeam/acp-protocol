import * as crypto from 'crypto';

export type TargetType = 
  | 'AGENT' | 'CLUSTER' | 'TOPIC' | 'BROKER' | 'SCHEDULER' 
  | 'MEMORY' | 'DISCOVERY' | 'HUMAN' | 'TOOL' | 'DATABASE' | 'ROBOT' | 'API' | 'BROWSER';

export type FrameType = 
  | 'REQUEST' | 'RESPONSE' | 'STREAM_CHUNK' | 'STREAM_END' | 'EVENT' 
  | 'NEGOTIATION_PROPOSAL' | 'NEGOTIATION_COUNTER' | 'NEGOTIATION_ACCEPT' | 'NEGOTIATION_REJECT' 
  | 'VOTE_CAST' | 'TASK_DELEGATION' | 'TASK_STATUS' | 'HEARTBEAT' | 'ERROR';

export interface Sender {
  agent_id: string;
  host_id: string;
  instance_id?: string;
  pubkey?: string;
}

export interface Receiver {
  target_type: TargetType;
  target_id?: string;
  routing_query?: Record<string, any>;
}

export interface Routing {
  hop_count: number;
  max_hops: number;
  reply_to?: string;
  trace_parent?: string;
  router_path: string[];
}

export interface Security {
  auth_token?: string;
  capability_token?: string;
  nonce: string;
  signature?: string;
  signature_alg: string;
  encryption_alg: string;
}

export class Envelope {
  acp_version: string = "1.0.0";
  message_id: string;
  correlation_id?: string;
  timestamp_ns: number;
  ttl_ms: number = 30000;
  sender: Sender;
  receiver: Receiver;
  frame_type: FrameType;
  routing: Routing;
  security: Security;
  payload: Record<string, any>;

  constructor(params: {
    sender: Sender;
    receiver: Receiver;
    frame_type: FrameType;
    payload?: Record<string, any>;
    correlation_id?: string;
    ttl_ms?: number;
  }) {
    this.message_id = crypto.randomUUID();
    this.timestamp_ns = Number(process.hrtime.bigint());
    this.correlation_id = params.correlation_id;
    if (params.ttl_ms) this.ttl_ms = params.ttl_ms;
    this.sender = params.sender;
    this.receiver = params.receiver;
    this.frame_type = params.frame_type;
    this.payload = params.payload || {};
    this.routing = { hop_count: 0, max_hops: 16, router_path: [] };
    this.security = {
      nonce: crypto.randomBytes(16).toString('hex'),
      signature_alg: 'HMAC-SHA256',
      encryption_alg: 'NONE'
    };
  }

  toCanonicalJson(): string {
    const data = {
      acp_version: this.acp_version,
      message_id: this.message_id,
      timestamp_ns: this.timestamp_ns,
      sender: this.sender,
      receiver: this.receiver,
      frame_type: this.frame_type,
      nonce: this.security.nonce,
      payload: this.payload
    };
    return JSON.stringify(data, Object.keys(data).sort());
  }

  sign(secretKey: string): string {
    const hmac = crypto.createHmac('sha256', secretKey);
    hmac.update(this.toCanonicalJson());
    const sig = hmac.digest('base64');
    this.security.signature = sig;
    return sig;
  }

  verifySignature(secretKey: string): boolean {
    if (!this.security.signature) return false;
    const hmac = crypto.createHmac('sha256', secretKey);
    hmac.update(this.toCanonicalJson());
    const expected = hmac.digest('base64');
    return crypto.timingSafeEqual(Buffer.from(this.security.signature), Buffer.from(expected));
  }
}
