export * from './envelope';

export class ACPClient {
  private endpoint: string;
  private did: string;
  private secretKey?: string;

  constructor(params: { endpoint: string; did: string; secretKey?: string }) {
    this.endpoint = params.endpoint;
    this.did = params.did;
    this.secretKey = params.secretKey;
  }

  static async connect(params: { endpoint: string; did: string; secretKey?: string }): Promise<ACPClient> {
    return new ACPClient(params);
  }

  async sendFrame(frame: any): Promise<any> {
    // Reference transport implementation abstraction
    return { status: "SUCCESS", frame_id: frame.message_id };
  }
}
