import { create } from 'zustand';

interface CountryData {
    name: string;
    code: string;
}

type Adtype = "custom" | "default"
export type ForecastType = 0 | 7 | 14 

interface AdRequest {
    product_name: string;
    product_summary: string;
    offer_summary: string;
    cta: string;
    locations: CountryData[];
    ad_type: Adtype;
    slot_reservation_id: string | null;
    use_weather: boolean;
    forecast_type: ForecastType | null;
    clone_language: string | null;
}

interface AdRequestState {
    disableNextButton: boolean;
    voiceCloningSentences: string[];

    productName: string;
    productSummary: string;
    offerSummary: string;
    cta: string;
    locations: CountryData[];
    adType: Adtype;
    reservationId: string | null;
    forecastType: ForecastType;
    cloneLanguage: string | null;
    cloneRecordings: ArrayBuffer[];

    setDisableNextButton: (data: boolean) => void;
    setVoiceCloningSentences: (data: string[]) => void;
    setProductName: (data: string) => void;
    setProductSummary: (data: string) => void;
    setOfferSummary: (data: string) => void;
    setCTA: (data: string) => void;
    setLocations: (data: CountryData[]) => void;
    setAdType: (data: Adtype) => void;
    setReservationId: (data: string | null) => void;
    setForecastType: (data: ForecastType) => void;
    setCloneLanguage: (data: string) => void;
    setCloneRecordings: (data: ArrayBuffer[]) => void
    getRequestObject: () => AdRequest
}

const defaultCloningSentences = [
    'When the sunlight strikes raindrops in the air, they act like a prism and form a rainbow. The rainbow is a division of white light into many beautiful colors',
    'The north wind and the sun were disputing which was the stronger, when a traveler came along wrapped in a warm cloak',
    'You wish to know all about my grandfather? Well, he’s dead now, but he lived in the Bighorn Mountains all of his life',
    'Sphinx of black quartz, judge my vow. A quick movement of the enemy will jeopardize six gunboats',
]


export const useAdRequest = create<AdRequestState>((set, get) => ({
    disableNextButton: true,
    voiceCloningSentences: defaultCloningSentences,

    productName: '',
    productSummary: '',
    offerSummary: '',
    cta: '',
    locations: [],
    adType: "default" as Adtype,
    reservationId: null,
    forecastType: 0,
    cloneLanguage: null,
    cloneRecordings: [],


    setDisableNextButton: (data) => set({ disableNextButton: data }),
    setVoiceCloningSentences: (data) => set({ voiceCloningSentences: data }),
    setProductName: (data) => set({ productName: data }),
    setProductSummary: (data) => set({ productSummary: data }),
    setOfferSummary: (data) => set({ offerSummary: data }),
    setCTA: (data) => set({ cta: data }),
    setLocations: (data) => set({ locations: data }),
    setAdType: (data) => set({ adType: data }),
    setReservationId: (data) => set({ reservationId: data }),
    setForecastType: (data) => set({ forecastType: data }),
    setCloneLanguage: (data) => set({ cloneLanguage: data }),
    setCloneRecordings: (data) => set({ cloneRecordings: data }),
    getRequestObject: () => {
        const forecastType = get().forecastType

        const requestData: AdRequest = {
            product_name: get().productName,
            ad_type: get().adType,
            clone_language: get().cloneLanguage,
            product_summary: get().productSummary,
            offer_summary: get().offerSummary,
            forecast_type: forecastType === 0 ? null : forecastType,
            use_weather: forecastType === 0 ? false : true,
            locations: get().locations,
            cta: get().cta,
            slot_reservation_id: get().reservationId
        }

        return requestData
    }
}))