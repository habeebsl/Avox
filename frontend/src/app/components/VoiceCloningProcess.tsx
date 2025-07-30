'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { MicrophoneIcon, CheckIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid';

interface AudioRecordingComponentProps {
  sentences: string[];
  onComplete: (recordings: ArrayBuffer[]) => void;
}

const AudioRecordingComponent: React.FC<AudioRecordingComponentProps> = ({ 
  sentences, 
  onComplete 
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState<ArrayBuffer[]>([]);
  const [timeLeft, setTimeLeft] = useState(25);
  const [hasStarted, setHasStarted] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isRequestingMic, setIsRequestingMic] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  // const [isComplete, setIsComplete] = useState(false)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const animationRef = useRef<number | null>(null);

  // Start recording for current sentence
  const startRecording = useCallback(async () => {
    if (sentences.length === 0) return;
    
    setIsRequestingMic(true);
    setMicError(null);
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setIsRequestingMic(false);
      
      // Set up audio context for visual feedback
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);

      // Set up MediaRecorder
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      const chunks: Blob[] = [];
      
      mediaRecorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };
      
      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        const blob = new Blob(chunks, { type: 'audio/wav' });
        const arrayBuffer = await blob.arrayBuffer();
        setRecordings(prev => [...prev, arrayBuffer]);
        setIsProcessing(false);
        
        // Clean up
        stream.getTracks().forEach(track => track.stop());
        if (audioContextRef.current) {
          audioContextRef.current.close();
        }
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      setTimeLeft(25);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            handleNext();
            return 25;
          }
          return prev - 1;
        });
      }, 1000);
      
      // Start audio level monitoring
      const updateAudioLevel = () => {
        if (analyserRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
          setAudioLevel(average / 255);
        }
        animationRef.current = requestAnimationFrame(updateAudioLevel);
      };
      updateAudioLevel();
      
    } catch (error) {
      setIsRequestingMic(false);
      setMicError('Unable to access microphone. Please check your permissions and try again.');
      console.error('Error accessing microphone:', error);
    }
  }, [sentences.length]);

  // Stop current recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      setAudioLevel(0);
    }
  }, [isRecording]);

  // Move to next sentence
  const handleNext = useCallback(() => {
    stopRecording();
    
    if (currentIndex < sentences.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setTimeLeft(25);
    } else {
      // All sentences completed - increment currentIndex to trigger completion
      setCurrentIndex(prev => prev + 1); // This makes isComplete = true
      setTimeout(() => {
        onComplete(recordings);
      }, 500);
    }
  }, [currentIndex, sentences.length, recordings, stopRecording, onComplete]);

  // Start recording when sentence changes
  useEffect(() => {
    if (hasStarted && currentIndex < sentences.length) {
      const timeout = setTimeout(() => {
        startRecording();
      }, 1000);
      
      return () => clearTimeout(timeout);
    }
  }, [currentIndex, hasStarted, startRecording, sentences.length]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  const handleStart = () => {
    setHasStarted(true);
  };

  const currentSentence = sentences[currentIndex];
  const timerProgress = ((30 - timeLeft) / 30) * 100;
  const isComplete = currentIndex >= sentences.length;

  // Empty state
  if (sentences.length === 0) {
    return (
      <div className="bg-black min-h-screen flex items-center justify-center p-8">
        <div className="max-w-2xl mx-auto text-center">
          <ExclamationTriangleIcon className="w-16 h-16 text-gray-400 mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-white mb-4">No Sentences Provided</h2>
          <p className="text-gray-400 text-lg">
            Please provide sentences to record before starting the voice cloning process.
          </p>
        </div>
      </div>
    );
  }

  // Microphone error state
  if (micError) {
    return (
      <div className="bg-black min-h-screen flex items-center justify-center p-8">
        <div className="max-w-2xl mx-auto text-center">
          <ExclamationTriangleIcon className="w-16 h-16 text-red-400 mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-white mb-4">Microphone Access Required</h2>
          <p className="text-gray-300 text-lg mb-8">{micError}</p>
          <button
            onClick={() => {
              setMicError(null);
              startRecording();
            }}
            className="bg-white text-black px-8 py-4 rounded-2xl font-semibold text-lg hover:bg-gray-200 transition-all duration-200 transform hover:scale-105"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!hasStarted) {
    return (
      <div className="bg-black min-h-screen flex items-center justify-center p-8">
        <div className="max-w-2xl mx-auto text-center">
          <MicrophoneIcon className="w-16 h-16 text-white mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-white mb-6">Voice Recording Setup</h2>
          <p className="text-gray-300 text-lg leading-relaxed mb-8">
            We need you to record a small number of audio samples so we can clone your voice 
            and use it for your personalized audio advertisement. This process will take just a few minutes.
          </p>
          <div className="bg-gray-900 rounded-2xl p-6 mb-8">
            <h3 className="text-white font-semibold mb-4">What to expect:</h3>
            <ul className="text-gray-300 text-left space-y-2">
              <li>• You'll see {sentences.length} sentences to read aloud</li>
              <li>• Each recording has a 30-second time limit</li>
              <li>• Recording starts automatically when each sentence appears</li>
              <li>• Speak clearly and naturally</li>
            </ul>
          </div>
          
          <button
            onClick={handleStart}
            className="bg-white text-black px-8 py-4 rounded-[8px] font-semibold text-lg hover:bg-gray-300"
          >
            Start Recording
          </button>
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="bg-black min-h-screen flex items-center justify-center p-8">
        <div className="max-w-2xl mx-auto text-center">
          <CheckIcon className="w-16 h-16 text-green-400 mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-white mb-4">Recording Complete!</h2>
          <p className="text-gray-300 text-lg">
            Thank you! We've successfully recorded {recordings.length} audio samples. 
            Your voice clone is being processed.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-black min-h-screen p-8 pb-0">
      <div className="max-w-4xl mx-auto">
        
        {/* Fixed Dots Section */}
        <div className="flex justify-center gap-2 mb-15">
          {sentences.map((_, index) => (
            <div
              key={index}
              className={`w-3 h-3 rounded-full transition-all duration-300 ${
                index < currentIndex
                  ? 'bg-white'
                  : index === currentIndex
                  ? 'bg-green-400 scale-125'
                  : 'bg-gray-700'
              }`}
            />
          ))}
        </div>

        {/* Fixed Sentence Section */}
        <div className="mb-16">
          <div className="text-center h-32 flex items-center justify-center">
            {isProcessing ? (
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mb-4"></div>
                <p className="text-gray-400">Processing recording...</p>
              </div>
            ) : (
              <h2 
                key={currentIndex}
                className="text-4xl font-light text-white leading-relaxed max-w-3xl animate-fade-in"
              >
                "{currentSentence}"
              </h2>
            )}
          </div>
        </div>

        {/* Fixed Recording Status Section */}
        <div className="mb-16">
          <div className="h-48 flex items-center justify-center">
            {isRequestingMic ? (
              <div className="flex flex-col items-center">
                <div className="animate-pulse bg-gray-700 p-4 rounded-full mb-4">
                  <MicrophoneIcon className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-gray-400">Requesting microphone access...</p>
              </div>
            ) : isRecording ? (
              <div className="flex flex-col items-center">
                {/* Timer Circle */}
                <div className="relative mb-4">
                  <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
                    <circle
                      cx="50"
                      cy="50"
                      r="45"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="transparent"
                      className="text-gray-700"
                    />
                    <circle
                      cx="50"
                      cy="50"
                      r="45"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="transparent"
                      strokeDasharray={`${2 * Math.PI * 45}`}
                      strokeDashoffset={`${2 * Math.PI * 45 * (1 - timerProgress / 100)}`}
                      className="text-red-500 transition-all duration-1000 ease-linear"
                    />
                  </svg>
                  
                  {/* Microphone with Audio Level */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div 
                      className="absolute inset-0 bg-red-500 rounded-full animate-pulse"
                      style={{ 
                        transform: `scale(${1 + audioLevel * 0.3})`,
                        opacity: 0.2 + audioLevel * 0.3 
                      }}
                    />
                    <div className="relative bg-red-500 p-3 rounded-full">
                      <MicrophoneIcon className="w-6 h-6 text-white" />
                    </div>
                  </div>
                </div>
                
                <p className="text-red-400 font-medium mb-2">Recording in progress...</p>
                <div className="text-white text-lg font-mono mb-4">
                  {timeLeft}s
                </div>
                
                {/* Audio Level Bars */}
                <div className="flex items-center gap-1">
                  {Array.from({ length: 12 }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-1.5 bg-gray-600 rounded-full transition-all duration-100 ${
                        i < audioLevel * 12 ? 'bg-white h-8' : 'h-3'
                      }`}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="bg-gray-800 p-4 rounded-full mb-4">
                  <MicrophoneIcon className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-gray-400">Preparing to record...</p>
              </div>
            )}
          </div>
        </div>

        {/* Fixed Button Section */}
        <div className="mb-8">
          <div className="flex justify-center">
            <button
              onClick={handleNext}
              disabled={!isRecording}
              className={`px-8 py-3 rounded-[7px] font-medium ${
                isRecording
                  ? 'bg-white text-black hover:bg-gray-300'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed'
              }`}
            >
              {currentIndex === sentences.length - 1 ? 'Finish' : 'Next Sentence'}
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
      `}</style>
    </div>
  );
};

export default AudioRecordingComponent;