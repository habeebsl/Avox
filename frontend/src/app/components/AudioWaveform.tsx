'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import styles from './AudioWaveform.module.css';
import useAudioStore from '../store/audioStore';
import { PlayButton } from './PlayButton';
import useAdData from '../store/adDataStore';
import { RecordHolder } from './RecordHolder';
import Loader from './Loader';

interface SmoothSplineWaveformProps {
  width?: number;
  height?: number;
  lineWidth?: number;
  className?: string;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const SmoothSplineWaveform: React.FC<SmoothSplineWaveformProps> = ({
  width = 800,
  height = 200,
  lineWidth = 3,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const animationRef = useRef<number>(0);
  const smoothedDataRef = useRef<number[]>([]);
  const progressRef = useRef<HTMLDivElement>(null);
  const glassBallRef = useRef<HTMLDivElement>(null);
  const isInitialLoadRef = useRef(true);
  
  // Local state for audio analysis and music toggle
  const [isDragging, setIsDragging] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isMusicEnabled, setIsMusicEnabled] = useState(true);
  
  const { 
    activeIndex, 
    getActiveAd, 
    getAdLoadingState, 
    getAdErrorState, 
    getAvailableAudioSources,
    hasAdWithAudio 
  } = useAdData()
  
  const activeAd = getActiveAd();
  const activeTheme = activeAd?.theme ?? "#008000"
  const musicAudioSrc = activeAd?.musicAudioSrc;
  const nonMusicAudioSrc = activeAd?.nonMusicAudioSrc;

  // Get audio availability info
  const audioSources = activeIndex !== null ? getAvailableAudioSources(activeIndex) : 
    { musicAvailable: false, nonMusicAvailable: false, hasAnyAudio: false };
  
  const hasBothVersions = audioSources.musicAvailable && audioSources.nonMusicAvailable;
  const hasOnlyMusic = audioSources.musicAvailable && !audioSources.nonMusicAvailable;
  const hasOnlyNonMusic = !audioSources.musicAvailable && audioSources.nonMusicAvailable;

  // Get loading and error states
  const isLoadingAudio = activeIndex !== null ? getAdLoadingState(activeIndex) : false;
  const isErrorAudio = activeIndex !== null ? getAdErrorState(activeIndex) : false;
  const hasAnyAudio = activeIndex !== null ? hasAdWithAudio(activeIndex) : false;

  // Determine the current audio source
  const getCurrentAudioSource = useCallback(() => {
    const isValidSource = (src: any): src is string => 
      typeof src === 'string' && src !== 'pending' && src !== 'error';
    
    if (hasOnlyMusic && isValidSource(musicAudioSrc)) return musicAudioSrc;
    if (hasOnlyNonMusic && isValidSource(nonMusicAudioSrc)) return nonMusicAudioSrc;
    
    if (isMusicEnabled && isValidSource(musicAudioSrc)) return musicAudioSrc;
    if (isValidSource(nonMusicAudioSrc)) return nonMusicAudioSrc;
    
    return undefined;
  }, [isMusicEnabled, musicAudioSrc, nonMusicAudioSrc, hasOnlyMusic, hasOnlyNonMusic]);

  const {
    currentTime,
    duration,
    isPlaying,
    audioContext,
    analyser,
    isInitialized,
    registerAudio,
    seekTo,
    play,
    pause,
    switchAudioSource,
    dataArray,
    resetAudio
  } = useAudioStore();

  // Register audio element with store
  useEffect(() => {
    if (audioRef.current) {
      const cleanup = registerAudio(audioRef.current);
      return cleanup;
    }
  }, [registerAudio, activeIndex]);

  // Set initial music state based on available versions
  useEffect(() => {
    if (hasOnlyNonMusic) {
      setIsMusicEnabled(false);
    } else {
      setIsMusicEnabled(true);
    }
  }, [hasOnlyNonMusic]);

  const handleMusicToggle = useCallback(async () => {
    const activeAd = getActiveAd()
    if (!audioRef.current || !hasBothVersions || !activeAd || activeAd.musicAudioSrc === "pending") return;
    
    const currentTimeStamp = audioRef.current.currentTime;
    const wasPlaying = !audioRef.current.paused;
    
    if (wasPlaying) {
      pause();
    }

    const newIsMusicEnabled = !isMusicEnabled;
    setIsMusicEnabled(newIsMusicEnabled);
    
    setTimeout(() => {
      const newSource = newIsMusicEnabled ? activeAd.musicAudioSrc : activeAd.nonMusicAudioSrc;
      
      if (newSource && typeof newSource === 'string' && audioRef.current) {
        resetAudio();
        
        audioRef.current.src = newSource;
        
        const handleLoadedMetadata = () => {
          if (audioRef.current) {
            audioRef.current.currentTime = currentTimeStamp;
            audioRef.current.removeEventListener('loadedmetadata', handleLoadedMetadata);
            
            if (wasPlaying) {
              setTimeout(() => play(), 100);
            }
          }
        };
        
        audioRef.current.addEventListener('loadedmetadata', handleLoadedMetadata);
        audioRef.current.load();
        
        if (switchAudioSource) {
          switchAudioSource(newSource);
        }
      }
    }, 50);
  }, [
    isMusicEnabled, 
    pause, 
    play, 
    resetAudio,
    switchAudioSource, 
    hasBothVersions,
    getActiveAd
  ]);

  const drawWaveformPath2D = useCallback(() => {
    if (!canvasRef.current || !analyser || !dataArray) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    analyser.getByteTimeDomainData(dataArray);
    
    const smoothed = smoothedDataRef.current;
    let totalVolume = 0;
    
    for (let i = 0; i < dataArray.length; i++) {
      smoothed[i] = smoothed[i] * 0.85 + dataArray[i] * 0.15;
      totalVolume += Math.abs(smoothed[i] - 128);
    }
    
    // Calculate audio level for glass ball scaling
    const avgVolume = totalVolume / dataArray.length;
    const normalizedLevel = Math.min(1, avgVolume / 50);
    setAudioLevel(normalizedLevel);

    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, width, height);

    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = activeTheme;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    const step = Math.floor(smoothed.length / 50);
    const points: { x: number; y: number }[] = [];

    for (let i = 0; i < smoothed.length; i += step) {
      const x = (i / smoothed.length) * width;
      const normalizedValue = (smoothed[i] - 128) / 128;
      const exaggeratedValue = Math.sign(normalizedValue) * Math.pow(Math.abs(normalizedValue), 0.1);
      const y = height / 2 + (exaggeratedValue * height * 0.4);
      points.push({ x, y });
    }

    const path = new Path2D();
    if (points.length > 0) {
      path.moveTo(points[0].x, points[0].y);
      
      for (let i = 1; i < points.length - 2; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        path.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
      }
      
      if (points.length > 2) {
        path.quadraticCurveTo(
          points[points.length - 2].x,
          points[points.length - 2].y,
          points[points.length - 1].x,
          points[points.length - 1].y
        );
      }
    }

    ctx.stroke(path);

    if (isPlaying) {
      animationRef.current = requestAnimationFrame(drawWaveformPath2D);
    }
  }, [analyser, dataArray, width, height, activeTheme, lineWidth, isPlaying]);

  const updateProgress = useCallback((clientX: number) => {
    if (!progressRef.current) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const clickX = clientX - rect.left;
    const progressWidth = rect.width;
    const clickRatio = Math.max(0, Math.min(1, clickX / progressWidth));
    const newTime = clickRatio * duration;
    
    seekTo(newTime);
  }, [duration, seekTo]);

  const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) {
      updateProgress(e.clientX);
    }
  }, [isDragging, updateProgress]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    setIsDragging(true);
    updateProgress(e.clientX);
  }, [updateProgress]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isDragging) {
      updateProgress(e.clientX);
    }
  }, [isDragging, updateProgress]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Global mouse event listeners for dragging
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  useEffect(() => {
    if (isPlaying && isInitialized) {
      drawWaveformPath2D();
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, isInitialized, drawWaveformPath2D]);

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (audioContext) {
        audioContext.close();
      }
    };
  }, [audioContext]);

  useEffect(() => {
    if (dataArray) {
      smoothedDataRef.current = new Array(dataArray.length).fill(128);
    }
  }, [dataArray])

  // Only auto-switch on initial load or when changing ads
  // Don't auto-switch when music arrives - let user toggle manually
  useEffect(() => {
    if (audioRef.current && activeIndex !== null && isInitialLoadRef.current) {
      // Get the active ad's audio sources at this moment
      const activeAd = getActiveAd();
      if (!activeAd) return;
      
      const isValidSource = (src: any): src is string => 
        typeof src === 'string' && src !== 'pending' && src !== 'error';
      
      // Start with non-music version if available (speech will load faster)
      let preferredSource: string | undefined;
      if (isValidSource(activeAd.nonMusicAudioSrc)) {
        preferredSource = activeAd.nonMusicAudioSrc;
      } else if (isValidSource(activeAd.musicAudioSrc)) {
        preferredSource = activeAd.musicAudioSrc;
      }
      
      if (preferredSource) {
        audioRef.current.src = preferredSource;
        audioRef.current.load();
        
        if (switchAudioSource) {
          switchAudioSource(preferredSource);
        }
        
        isInitialLoadRef.current = false;
      }
    }
  }, [
    activeIndex,  // Only re-run when switching ads
    getActiveAd,
    switchAudioSource
  ]);
  
  // Reset initial load flag when switching ads
  useEffect(() => {
    isInitialLoadRef.current = true;
  }, [activeIndex]);

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  const getTooltipText = () => {
    if (activeAd?.musicAudioSrc === "pending") {
      return "Background music is loading"
    }

    if (!hasBothVersions) return "Only one version available";
    return isMusicEnabled ? "Disable music" : "Enable music";
  };

  return (
    <div className={`${styles.container} ${className}`}>
      <div 
        ref={glassBallRef}
        className={styles.glassBall}
        style={{
          transform: `scale(${1 + audioLevel * 0.3})`,
          filter: `blur(${audioLevel * 2}px)`,
        }}
      >
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className={styles.canvas}
        />
      </div>
      
      <div className={styles.controls}>
        <div className={styles.controlRow}>
          <button
            onClick={handleMusicToggle}
            className={`${styles.musicButton} ${
              activeAd?.musicAudioSrc === "pending"
                ? styles.musicLoading
                : !hasBothVersions 
                  ? styles.musicDisabled 
                  : isMusicEnabled 
                    ? styles.musicEnabled 
                    : styles.musicDisabled
            }`}
            disabled={!hasBothVersions || activeAd?.musicAudioSrc === "pending"}
            title={getTooltipText()}
          >
            {activeAd?.musicAudioSrc === "pending" ? (
              <Loader color='black' size='sm' />
            ) : isMusicEnabled || hasOnlyMusic ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                {!hasBothVersions && (
                  <path d="M4.27 3L3 4.27L19.73 21L21 19.73L4.27 3z" opacity="0.5"/>
                )}
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                <path d="M4.27 3L3 4.27L19.73 21L21 19.73L4.27 3z"/>
              </svg>
            )}
          </button>

          <PlayButton 
            isDisabled={!hasAnyAudio}
            isPlaying={isPlaying}
            isLoading={isLoadingAudio}
            loaderSize='md'
            isError={isErrorAudio}
          />

        </div>
        
        <div className={styles.progressContainer}>
          <span className={styles.timeDisplay}>{formatTime(currentTime)}</span>
          <div 
            ref={progressRef}
            className={`${styles.progressBar} ${isDragging ? styles.dragging : ''}`}
            onClick={handleProgressClick}
            onMouseDown={handleMouseDown}
          >
            <div 
              className={styles.progressFill}
              style={{ width: `${progressPercentage}%` }}
            />
            <div 
              className={styles.progressHandle}
              style={{ left: `${progressPercentage}%` }}
            />
          </div>
          <span className={styles.timeDisplay}>{formatTime(duration)}</span>
        </div>
      </div>
      
      <audio
        ref={audioRef}
        src={getCurrentAudioSource()}
        preload="metadata"
      />
      <RecordHolder />
    </div>
  );
};

export default SmoothSplineWaveform;