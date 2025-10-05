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

  seekTo: (time) => {
    const { audioElement } = get();
    if (audioElement) {
      audioElement.currentTime = time;
    }
  },

  play: async () => {
    const { audioElement, audioContext, isPlaying } = get();
    console.log('▶️ [audioStore] play() called', {
      hasAudioElement: !!audioElement,
      audioContextState: audioContext?.state,
      currentIsPlaying: isPlaying,
      audioSrc: audioElement?.src,
      audioPaused: audioElement?.paused,
      audioReadyState: audioElement?.readyState
    });
    
    if (!audioElement) {
      console.warn('⚠️ [audioStore] Cannot play - no audio element');
      return;
    }

    if (audioContext?.state === 'suspended') {
      console.log('🔊 [audioStore] Resuming suspended audio context');
      await audioContext.resume();
    }

    try {
      console.log('▶️ [audioStore] Calling audioElement.play()');
      await audioElement.play();
      console.log('✅ [audioStore] audioElement.play() succeeded');
    } catch (error) {
      console.error('❌ [audioStore] Play failed:', error);
    }
  },

  pause: () => {
    const { audioElement } = get();
    console.log('⏸️ [audioStore] pause() called', {
      hasAudioElement: !!audioElement,
      audioPaused: audioElement?.paused,
      currentTime: audioElement?.currentTime
    });
    
    if (audioElement) {
      audioElement.pause();
      console.log('✅ [audioStore] audioElement.pause() executed');
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
    const { audioElement, isPlaying } = get();
    console.log('🔄 [audioStore] resetAudio() called', {
      hasAudioElement: !!audioElement,
      currentIsPlaying: isPlaying,
      currentTime: audioElement?.currentTime,
      audioPaused: audioElement?.paused
    });
    
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      console.log('✅ [audioStore] Audio reset - paused and seeked to 0');
    }
    
    set({
      currentTime: 0,
      isPlaying: false,
      isLoading: true,
      duration: 0,
    });
    
    console.log('✅ [audioStore] Store state reset');
  },
}));

export default useAudioStore;