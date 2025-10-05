import { isJsonString } from "../helpers/utils";
import { 
    ResponsePayload, 
    InsightsResponsePayload, 
    SpeechResponsePayload, 
    FinishedAdPayload,
    MergedAdPayload,
    AdErrorPayload
} from "../schemas/ws.schemas";
import useAdData from "../store/adDataStore";

interface WebSocketConnection {
    close: () => void;
    isConnected: () => boolean;
    getReadyState: () => number;
}

export const wsService = {
    generateAds(
        reqData: object, 
        musicBuffers: ArrayBuffer[] | null = null
    ): WebSocketConnection {
        let socket: WebSocket | null = null;
        let isConnected = false;
        const createdUrls = new Set<string>();

        const handleMessage = (message: MessageEvent) => {
            const data = message.data
            console.log("Received Message: ", data, typeof data)
            try {
                if (typeof data === 'string' || isJsonString(data)) {

                    handleJsonMessage(data);
                } else if (data instanceof Blob) {
                    handleBlobMessage(data);
                }
            } catch (err) {
                console.error("Failed to parse message:", err);
            }
        };

        const handleJsonMessage = (data: string | Buffer) => {
            const json = JSON.parse(data.toString());
            const resData = ResponsePayload.parse(json);
            console.log("Received JSON:", json);

            if (json.event === "transcription") {
                console.log("Transcript:", json.text);
                return;
            }

            const { updateAd, ads, nullifyAllPendingRequests } = useAdData.getState();
            let targetAd = null;

            console.log("Data Type: ", resData.type)
            
            if (resData.index !== undefined) {
                targetAd = ads.find(ad => ad.index === resData.index);
            }

            switch (resData.type) {
                case "insight":
                    if (targetAd) {
                        const insights_data = InsightsResponsePayload.parse(resData);
                        targetAd.insights = insights_data.insights;
                    }
                    break;

                case "done":
                    if (targetAd) {
                        FinishedAdPayload.parse(resData);
                        targetAd.status = "done";
                    }
                    break;
                
                case "complete":
                    nullifyAllPendingRequests()
                    break;
                
                case "error":
                    if (targetAd) {
                        handleAdError(targetAd, resData);
                    }
                    break;
            }

            if (targetAd) {
                updateAd(targetAd);
            }
        };

        const handleAdError = (targetAd: any, resData: any) => {
            const errorData = AdErrorPayload.parse(resData);

            switch (errorData.step) {
                case "merged":
                    targetAd.musicAudioSrc = "error";
                    break;
                
                case "speech":
                    targetAd.nonMusicAudioSrc = "error";
                    targetAd.transcriptSents = "error";
                    break;

                case "music":
                    targetAd.musicAudioSrc = "error";
                    break;
            
                default:
                    targetAd.musicAudioSrc = "error";
                    targetAd.nonMusicAudioSrc = "error";
                    targetAd.transcriptSents = "error";
                    targetAd.insights = "error";
                    break;
            }
        };

        const handleBlobMessage = (data: Blob) => {
            console.log("Received Blob Data")
            const reader = new FileReader();
            reader.onload = () => {
                const arrayBuffer = reader.result as ArrayBuffer;
                const dataView = new DataView(arrayBuffer);

                const metaLength = dataView.getUint32(0, true);
                const metaBytes = new Uint8Array(arrayBuffer, 4, metaLength);
                const metadata = ResponsePayload.parse(
                    JSON.parse(new TextDecoder().decode(metaBytes))
                );
                console.log("Blob Metadata: ", metadata)

                const audioBytes = arrayBuffer.slice(4 + metaLength);
                const blob = new Blob([audioBytes], { type: "audio/mpeg" });
                const audioUrl = URL.createObjectURL(blob);
                console.log("Audio Url: ", audioUrl)


                createdUrls.add(audioUrl);

                const { updateAd, ads } = useAdData.getState();
                let targetAd = null;
                
                if (metadata.index !== undefined) {
                    targetAd = ads.find(ad => ad.index === metadata.index);
                }

                switch (metadata.type) {
                    case "speech":
                        if (targetAd) {
                            const speechData = SpeechResponsePayload.parse(metadata);
                            console.log('🎤 [WebSocket] Received speech audio', {
                                index: metadata.index,
                                audioUrl,
                                previousNonMusicSrc: targetAd.nonMusicAudioSrc
                            });
                            
                            targetAd.nonMusicAudioSrc = audioUrl;
                            targetAd.transcriptSents = speechData.alignments;
                            
                            if (speechData.translations) {
                                console.log("Received Translations: ", speechData.translations)
                                targetAd.englishTranscriptSents = speechData.transcript.split("\n");
                            }

                            console.log("Target Ad: ", targetAd)
                        }
                        break;
                    
                    case "merged":
                        if (targetAd) {
                            MergedAdPayload.parse(metadata);
                            console.log('🎵 [WebSocket] Received merged (music) audio', {
                                index: metadata.index,
                                audioUrl,
                                previousMusicSrc: targetAd.musicAudioSrc,
                                currentNonMusicSrc: targetAd.nonMusicAudioSrc
                            });
                            
                            targetAd.musicAudioSrc = audioUrl;
                        }
                        break;
                }

                if (targetAd) {
                    updateAd(targetAd);
                }
            };
            
            reader.onerror = () => {
                console.error("Failed to read blob data");
            };
            
            reader.readAsArrayBuffer(data);
        };

        try {
            const { failAllPendingRequests } = useAdData.getState()
            const wsUrl = `${process.env.NEXT_PUBLIC_WS_BASE}/ws/ads/generate`;
            console.log("🔗 Attempting WebSocket connection to:", wsUrl);
            socket = new WebSocket(wsUrl);

            socket.addEventListener('open', () => {
                console.log("WebSocket connection opened");
                isConnected = true;

                if (socket) {
                    socket.send(JSON.stringify(reqData));
                    
                    if (musicBuffers) {
                        musicBuffers.forEach(buffer => {
                            socket?.send(buffer);
                        });
                    }
                    
                    socket.send(JSON.stringify({ "type": "finished" }));
                }
            });

            socket.addEventListener('message', handleMessage);

            socket.addEventListener('close', (event) => {
                console.log("WebSocket connection closed", event.code, event.reason);
                isConnected = false;
                failAllPendingRequests()
            });

            socket.addEventListener('error', (error) => {
                console.error("WebSocket error:", error);
                isConnected = false;
                failAllPendingRequests()
            });

        } catch (error) {
            console.error("Failed to create WebSocket connection:", error);
            const { failAllPendingRequests } = useAdData.getState()
            failAllPendingRequests()
        }

        return {
            close: () => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.close();
                }
            },
            isConnected: () => isConnected,
            getReadyState: () => socket?.readyState ?? WebSocket.CLOSED
        };
    }
};