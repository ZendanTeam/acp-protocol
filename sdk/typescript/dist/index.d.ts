export * from './envelope';
export declare class ACPClient {
    private endpoint;
    private did;
    private secretKey?;
    constructor(params: {
        endpoint: string;
        did: string;
        secretKey?: string;
    });
    static connect(params: {
        endpoint: string;
        did: string;
        secretKey?: string;
    }): Promise<ACPClient>;
    sendFrame(frame: any): Promise<any>;
}
