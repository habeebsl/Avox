'use client'

import { PlayButton } from "./PlayButton"
import useAdData from "../store/adDataStore";
import useAudioStore from "../store/audioStore";
import useNotificationStore from "../store/notificationStore";
import { useMemo, useEffect } from "react";

interface AdCubeProps {
  index: number;
  theme?: string;
}

export const AdCube: React.FC<AdCubeProps> = ({
  index,
  theme = '#8B5CF6'
}) => {

  const { 
    setActiveIndex, 
    hasAdWithAudio, 
    getActiveAd,
    ads,
    getAdLoadingState,
    getAdErrorState
  } = useAdData()

  const { isPlaying, pause } = useAudioStore()
  const { setActiveTrack, handleTrackUpdate } = useNotificationStore()
  
  const currentAd = ads[index];
  const activeAd = getActiveAd();
  const isActive = activeAd?.index === index;

  useEffect(() => {
    if (!currentAd) return;

    const musicReady = currentAd.musicAudioSrc && 
                      currentAd.musicAudioSrc !== "pending" && 
                      currentAd.musicAudioSrc !== "error";
    const voiceReady = currentAd.nonMusicAudioSrc && 
                      currentAd.nonMusicAudioSrc !== "pending" && 
                      currentAd.nonMusicAudioSrc !== "error";
    const hasError = currentAd.musicAudioSrc === "error" || 
                    currentAd.nonMusicAudioSrc === "error";
    const isLoading = currentAd.musicAudioSrc === "pending" || 
                     currentAd.nonMusicAudioSrc === "pending";

    if (hasError) {
      handleTrackUpdate(index, 'error');
    } else if (musicReady || voiceReady) {
      console.log(`${musicReady ? "music ready" : voiceReady ? "voice ready" : ""}`)
      handleTrackUpdate(index, 'ready');
    } else if (isLoading) {
      handleTrackUpdate(index, 'loading');
    }
  }, [currentAd?.musicAudioSrc, currentAd?.nonMusicAudioSrc, index, handleTrackUpdate]);
     
  const handleClick = async () => {
    setActiveTrack(index) // Set as active track for notifications
  
    const currentAd = getActiveAd()
    if (currentAd?.index === index && isPlaying) {
      return
    }
    
    if (currentAd?.index !== index && isPlaying) {
      pause()
    }
    
    setActiveIndex(index)
  }

  const isAdCurrentlyPlaying = useMemo(() => {
    const ad = getActiveAd()
    return ad?.index === index && isPlaying
  }, [getActiveAd, index, isPlaying])

  // Rest of your component remains the same...
  const LocationIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
    </svg>
  );

  return (
    <div 
      onClick={handleClick} 
      className="relative flex items-center justify-between p-4 backdrop-blur-20 border-b border-white/10 transition-all duration-300 hover:bg-white/10 group cursor-pointer"
      style={{
        borderBottomColor: 'rgba(255, 255, 255, 0.1)',
        borderBottomWidth: '1px'
      }}
    >
      {/* Content container */}
      <div className="flex items-center gap-3 flex-1">
        <PlayButton 
          isDisabled={!hasAdWithAudio(index)}
          isPlaying={isAdCurrentlyPlaying}
          playButtonStyling="w-[32px] h-[32px] backdrop-blur-lg"
          svgStyling="w-[16px] h-[16px] text-white"
          theme={theme}
          isLoading={currentAd.status === "pending"}
          loaderSize="sm"
          isError={getAdErrorState(index)}
        />
        <div className="flex flex-col gap-1 flex-1">
          <div className="flex justify-between items-center gap-2">
            <span className="text-white/80 font-medium text-sm">
              Track {index + 1}
            </span>
            <div className="flex items-center gap-1 text-white/60 text-xs">
              <LocationIcon />
              <span>{currentAd?.location}</span>
            </div>
          </div>
          
          {/* Optional: Add duration or other metadata */}
          <div className="text-white/50 text-xs">
            {hasAdWithAudio(index) ? 'Audio available' : 'No audio'}
          </div>
        </div>
      </div>

      {/* Active indicator */}
      {isActive && (
        <div 
          className="absolute left-0 top-0 bottom-0 w-0.5 bg-white/60 rounded-r-full" 
        />
      )}
    </div>
  )
}