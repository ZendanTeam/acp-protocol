export type TargetType = 'AGENT' | 'CLUSTER' | 'TOPIC' | 'BROKER' | 'SCHEDULER' | 'MEMORY' | 'DISCOVERY' | 'HUMAN' | 'TOOL' | 'DATABASE' | 'ROBOT' | 'API' | 'BROWSER';
export type FrameType = 'REQUEST' | 'RESPONSE' | 'STREAM_CHUNK' | 'STREAM_END' | 'EVENT' | 'NEGOTIATION_PROPOSAL' | 'NEGOTIATION_COUNTER' | 'NEGOTIATION_ACCEPT' | 'NEGOTIATION_REJECT' | 'VOTE_CAST' | 'TASK_DELEGATION' | 'TASK_STATUS' | 'HEARTBEAT' | 'ERROR';
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
export declare class Envelope {
    acp_version: string;
    message_id: string;
    correlation_id?: string;
    timestamp_ns: number;
    ttl_ms: number;
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
    });
    toCanonicalJson(): string;
    sign(secretKey: string): string;
    verifySignature(secretKey: string): boolean;
}
