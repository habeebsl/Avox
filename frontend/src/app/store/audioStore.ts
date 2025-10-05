import { create } from 'zustand';

interface AudioState {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  isLoading: boolean;
  audioElement: HTMLAudioElement | null;
  audioContext: AudioContext | null;
  dataArray: Uint8Array | null;
  analyser: AnalyserNode | null;
  isInitialized: boolean;
  currentSource: string;
  
  cleanup: (() => void) | null;
  
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setAudioContext: (context: AudioContext | null) => void;
  setAnalyser: (analyser: AnalyserNode | null) => void;
  setIsInitialized: (initialized: boolean) => void;
  setDataArray: (data: Uint8Array | null) => void; 
  
  registerAudio: (audioElement: HTMLAudioElement) => (() => void);
  initializeAudio: () => Promise<{ dataArray: Uint8Array; analyser: AnalyserNode } | null>;
  reinitializeAudio: () => Promise<{ dataArray: Uint8Array; analyser: AnalyserNode } | null>;
  seekTo: (time: number) => void;
  play: () => Promise<void>;
  pause: () => void;
  switchAudioSource: (newSource: string) => void;
  reset: () => void;
  resetAudio: () => void;
}

const useAudioStore = create<AudioState>((set, get) => ({
  // Initial state
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  isLoading: true,
  audioElement: null,
  audioContext: null,
  analyser: null,
  isInitialized: false,
  currentSource: '',
  cleanup: null,
  dataArray: null,
  
  // Actions
  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setAudioContext: (context) => set({ audioContext: context }),
  setAnalyser: (analyser) => set({ analyser }),
  setIsInitialized: (initialized) => set({ isInitialized: initialized }),
  setDataArray: (data) => set({ dataArray: data }),
  
  registerAudio: (audioElement) => {
    // Clean up previous listeners if any
    const { cleanup: existingCleanup } = get();
    if (existingCleanup) {
      existingCleanup();
    }

    const handleTimeUpdate = () => {
      set({ currentTime: audioElement.currentTime });
    };
    
    const handlePlay = () => set({ isPlaying: true });
    const handlePause = () => set({ isPlaying: false });
    const handleEnded = () => set({ isPlaying: false });
    const handleLoadedMetadata = () => {
      set({ 
        duration: audioElement.duration,
        isLoading: false 
      });
    };

    // Add event listeners
    audioElement.addEventListener('timeupdate', handleTimeUpdate);
    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('pause', handlePause);
    audioElement.addEventListener('ended', handleEnded);
    audioElement.addEventListener('loadedmetadata', handleLoadedMetadata);

    // Create cleanup function
    const cleanup = () => {
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('pause', handlePause);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };

    set({ audioElement, cleanup });
    return cleanup;
  },

  initializeAudio: async () => {
    const { audioElement, isInitialized } = get();
    
    if (!audioElement || isInitialized) {
      return null;
    }

    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyserNode = ctx.createAnalyser();
      
      analyserNode.fftSize = 512;
      analyserNode.smoothingTimeConstant = 0.7;
      
      const bufferLength = analyserNode.fftSize;
      const dataArray = new Uint8Array(bufferLength);
      
      const source = ctx.createMediaElementSource(audioElement);
      source.connect(analyserNode);
      analyserNode.connect(ctx.destination);
      
      set({
        audioContext: ctx,
        analyser: analyserNode,
        isInitialized: true,
        dataArray: dataArray
      });

      return { dataArray, analyser: analyserNode };
    } catch (error) {
      console.error('Audio initialization failed:', error);
      return null;
    }
  },

  reinitializeAudio: async () => {
    const { audioElement, audioContext } = get();
    
    if (!audioElement) {
      return null;
    }

    try {
      // Close old AudioContext if it exists
      if (audioContext) {
        await audioContext.close();
      }
      
      // Reset initialization state
      set({
        audioContext: null,
        analyser: null,
        isInitialized: false,
        dataArray: null
      });

      // Create new AudioContext and reconnect
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyserNode = ctx.createAnalyser();
      
      analyserNode.fftSize = 512;
      analyserNode.smoothingTimeConstant = 0.7;
      
      const bufferLength = analyserNode.fftSize;
      const dataArray = new Uint8Array(bufferLength);
      
      // Create new MediaElementSource with current audio element
      const source = ctx.createMediaElementSource(audioElement);
      source.connect(analyserNode);
      analyserNode.connect(ctx.destination);
      
      set({
        audioContext: ctx,
        analyser: analyserNode,
        isInitialized: true,
        dataArray: dataArray
      });

      return { dataArray, analyser: analyserNode };
    } catch (error) {
      console.error('Audio reinitialization failed:', error);
      return null;
    }
  },

  seekTo: (time) => {
    const { audioElement } = get();
    if (audioElement) {
      audioElement.currentTime = time;
    }
  },

  play: async () => {
    const { audioElement, audioContext } = get();
    if (!audioElement) return;

    if (audioContext?.state === 'suspended') {
      await audioContext.resume();
    }

    try {
      await audioElement.play();
    } catch (error) {
      console.error('Play failed:', error);
    }
  },

  pause: () => {
    const { audioElement } = get();
    if (audioElement) {
      audioElement.pause();
    }
  },

  switchAudioSource: (newSource) => {
    set({ currentSource: newSource });
  },

  reset: () => {
    const { cleanup } = get();
    if (cleanup) {
      cleanup();
    }
    
    set({
      currentTime: 0,
      duration: 0,
      isPlaying: false,
      isLoading: true,
      audioElement: null,
      audioContext: null,
      analyser: null,
      isInitialized: false,
      currentSource: '',
      cleanup: null,
    });
  },

  resetAudio: () => {
    const { audioElement } = get();
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
    
    set({
      currentTime: 0,
      isPlaying: false,
      isLoading: true,
      duration: 0,
    });
  },
}));

export default useAudioStore;