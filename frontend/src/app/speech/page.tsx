'use client';

import { useEffect } from "react";
import useAdData from "../store/adDataStore";
import { useAdRequest } from "../store/adRequestStore";
import { wsService } from "../services/ws";
import SmoothSplineWaveform from "../components/AudioWaveform";
import TranscriptSync from "../components/TranscriptSync";
import ToastContainer from "../components/ToastContainer";


export default function SpeechPage() {
  const { populateAds, setActiveIndex } = useAdData()
  const { locations, adType, cloneRecordings, getRequestObject } = useAdRequest()

  useEffect(() => {
    if (locations) {
      console.log(getRequestObject())
      if (adType === "custom" && cloneRecordings.length > 0) {
        populateAds(locations)
        setActiveIndex(0)
        wsService.generateAds(getRequestObject(), cloneRecordings)
      } 

      if (adType === "default") {
        populateAds(locations)
        setActiveIndex(0)
        wsService.generateAds(getRequestObject())
      }
    }
  }, [])
  
  return (
    <div className="bg-black flex h-screen w-full justify-between">
      <ToastContainer />
      <div className="w-[40%] flex justify-center items-center">
        <SmoothSplineWaveform
          width={300}
          height={300}
          lineWidth={30}
        />
      </div>

      <div className="w-[60%]">
        <TranscriptSync />
      </div>
    </div>
  );
}