import { useState, useEffect, useRef } from "react";

export interface SpeechRecognitionHook {
  isListening: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  clearTranscript: () => void;
  error: string | null;
  supported: boolean;
}

export function useSpeechRecognition(): SpeechRecognitionHook {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [supported, setSupported] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      setSupported(true);
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";

      rec.onstart = () => {
        setIsListening(true);
        setError(null);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      rec.onerror = (event: any) => {
        console.error("Speech Recognition Error:", event.error);
        if (event.error === "not-allowed") {
          setError("Microphone permission was denied.");
        } else if (event.error === "no-speech") {
          // Ignore no-speech errors to prevent visual clutter
        } else {
          setError(`Service message: ${event.error}`);
        }
        setIsListening(false);
      };

      rec.onresult = (event: any) => {
        let finalTranscript = "";
        let interimTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        
        // Output either final accumulation or interim guessing context
        const fullOutput = finalTranscript || interimTranscript;
        setTranscript(fullOutput);
      };

      recognitionRef.current = rec;
    } else {
      setSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // Safe block
        }
      }
    };
  }, []);

  const startListening = () => {
    if (!supported || !recognitionRef.current) return;
    try {
      setTranscript("");
      setError(null);
      recognitionRef.current.start();
    } catch (e) {
      console.error("Error starting voice recognition:", e);
    }
  };

  const stopListening = () => {
    if (!supported || !recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {
      console.error("Error ending voice recognition:", e);
    }
  };

  const clearTranscript = () => {
    setTranscript("");
  };

  return {
    isListening,
    transcript,
    startListening,
    stopListening,
    clearTranscript,
    error,
    supported,
  };
}


