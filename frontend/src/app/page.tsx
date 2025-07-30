"use client"

import { useState } from "react";
import { useRouter } from "next/navigation";
import ErrorNotification from "./components/ErrorNotification";
import VoiceSelectionForm from "./components/Forms/VoiceSelectionForm";
import AudioRecordingComponent from "./components/VoiceCloningProcess";
import ProductForm from "./components/Forms/ProductForm";
import Loader from "./components/Loader";
import { useAdRequest } from "./store/adRequestStore";
import useError from "./store/errorStore";
import { apiService } from "./services/api";
import { CloningSentencesPayload, ReservationIdPayload } from "./schemas/api.schemas";


export default function Home() {
  const router = useRouter()
  const [currentForm, setCurrentForm] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [showNextButton, setShowNextButton] = useState(true)
  const { 
    disableNextButton, 
    setDisableNextButton,
    setReservationId,
    voiceCloningSentences, 
    setVoiceCloningSentences,
    cloneLanguage,
    setCloneRecordings,
    adType,
  } = useAdRequest()

  const { 
    title,
    message,
    showError,
    setMessage, 
    setTitle, 
    setShowError 
  } = useError()

  const handleRecordingComplete = (recordings: ArrayBuffer[]) => {
    console.log('All recordings completed!', recordings);
    setCloneRecordings(recordings)
    router.push("/speech")
  };

  async function getCloningSents () {
    try {
      setIsLoading(true)
      if (!cloneLanguage) return

      const response = await apiService.getVoiceTrainingSents(cloneLanguage)
      const data = CloningSentencesPayload.parse(response.data)

      setVoiceCloningSentences(data.sentences)

      return data
    } catch (error) {
      console.error("Error while getting cloning sentences: ", error)
    } finally {
      setIsLoading(false)
    }
  }

  async function fetchReservationId() {
    try {
      setIsLoading(true)
      const response = await apiService.createReservation()
      const data = ReservationIdPayload.parse(response.data)
      
      setReservationId(data.reservation_id || null)

      return data
    } catch (error) {
      console.error("Error while fetching reservation ID: ", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleNext = async () => {
    console.log("Next clicked!")
    setDisableNextButton(true)

    if (currentForm === 1) {
      setShowNextButton(false)
      if (adType === "custom") {
        const data = await fetchReservationId()

        if (!data || !data.created) {
          setDisableNextButton(true)
          setShowNextButton(true)
          setCurrentForm(0)
          setTimeout(() => {
            setTitle("Cloning Unavailable")
            setMessage("Voice cloning is unavailable right now. Try again later.")
            setShowError(true)
          }, 500);
          return
        }

        const sentsData = await getCloningSents() 

        if (!sentsData) {
          setDisableNextButton(true)
          setShowNextButton(true)
          setCurrentForm(0)
          setTimeout(() => {
            setTitle("Error Getting Cloning sentences")
            setMessage("We couldn't retreive the voice cloning sentences. Try again later.")
            setShowError(true)
          }, 500);
          return
        }
      } else {
        router.push("/speech")
        return
      }
    }

    setCurrentForm(prev => prev + 1)

    console.log(currentForm)
  }

  if (isLoading) {
    return (
      <div className="bg-black w-full h-screen flex flex-col gap-4 justify-center items-center">
        <Loader color="white" />
        <p className="text-[25px] font-medium text-white mb-4">Getting Ready...</p>
      </div>
    )
  }

  return (
    <>
      {currentForm === 0 ? (
        <VoiceSelectionForm />
      ) : currentForm === 1 ? (
        <ProductForm />
      ) : currentForm === 2 ? (
        <AudioRecordingComponent 
          sentences={voiceCloningSentences} 
          onComplete={handleRecordingComplete} 
        />
      ) : null}

      {showNextButton && (
        <div className="fixed right-4 top-20 md:right-50">
          <button
            onClick={handleNext}
            disabled={disableNextButton}
            className={`px-6 py-3 md:px-8 rounded-[7px] font-medium text-sm md:text-base min-w-[80px] ${
              !disableNextButton
                ? 'bg-white text-black hover:bg-gray-300 active:bg-gray-400'
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
            }`}
          >
            Next
          </button>
        </div>
      )}
      
      <ErrorNotification
        title={title}
        message={message}
        isVisible={showError}
        onClose={() => setShowError(false)}
      />
    </>
  );
}