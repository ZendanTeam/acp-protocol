"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.Envelope = void 0;
const crypto = __importStar(require("crypto"));
class Envelope {
    acp_version = "1.0.0";
    message_id;
    correlation_id;
    timestamp_ns;
    ttl_ms = 30000;
    sender;
    receiver;
    frame_type;
    routing;
    security;
    payload;
    constructor(params) {
        this.message_id = crypto.randomUUID();
        this.timestamp_ns = Number(process.hrtime.bigint());
        this.correlation_id = params.correlation_id;
        if (params.ttl_ms)
            this.ttl_ms = params.ttl_ms;
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
    toCanonicalJson() {
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
    sign(secretKey) {
        const hmac = crypto.createHmac('sha256', secretKey);
        hmac.update(this.toCanonicalJson());
        const sig = hmac.digest('base64');
        this.security.signature = sig;
        return sig;
    }
    verifySignature(secretKey) {
        if (!this.security.signature)
            return false;
        const hmac = crypto.createHmac('sha256', secretKey);
        hmac.update(this.toCanonicalJson());
        const expected = hmac.digest('base64');
        return crypto.timingSafeEqual(Buffer.from(this.security.signature), Buffer.from(expected));
    }
}
exports.Envelope = Envelope;
