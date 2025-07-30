'use client'

import React, { useCallback } from "react";
import useAudioStore from "../store/audioStore";
import styles from './PlayButton.module.css';
import Loader from "./Loader";
import ErrorIcon from "./ErrorIcon";
import clsx from "clsx";


interface PlayButtonProps {
  isDisabled: boolean;
  isPlaying: boolean;
  playButtonStyling?: string;
  svgStyling?: string;
  theme?: string;
  isLoading?: boolean;
  loaderSize?: "sm" | "md" | "lg" | "xl";
  isError?: boolean;
}

export const PlayButton: React.FC<PlayButtonProps> = ({ 
  isDisabled, 
  isPlaying, 
  playButtonStyling = 'w-[48px] h-[48px] backdrop-blur-sm', 
  svgStyling  = 'w-[24px] h-[24px]',
  theme = 'white',
  isLoading = false,
  loaderSize = "sm",
  isError = false
}) => {
  const { 
    isInitialized,
    play, 
    pause,
    initializeAudio,
  } = useAudioStore()

  const handleInitializeAudio = useCallback(async () => {
    await initializeAudio();
  }, [initializeAudio]);

  const handlePlay = useCallback(async () => {
    if (!isInitialized) {
      await handleInitializeAudio();
    }

    setTimeout(async () => {
      await play();
    }, 100);
  }, [isInitialized, initializeAudio, play]);

  const handlePause = useCallback(() => {
    pause();
  }, [pause]);
  return (
    <button
      onClick={isPlaying ? handlePause : handlePlay}
      className={clsx(styles.playButton, playButtonStyling)}
      style={{ backgroundColor: theme }}
      disabled={isDisabled}
    >
      {isPlaying ? (
        <svg className={svgStyling} width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
        </svg>
      ) : isLoading ? (
          <Loader color="black" size={loaderSize} />
      ) : isError ? (
        <ErrorIcon />
      ) : (
        <svg className={svgStyling} width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M8 5v14l11-7z"/>
        </svg>
      )}
    </button>
  )
}