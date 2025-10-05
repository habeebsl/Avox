import { create } from 'zustand';
import { Sentence, Insight } from '../types/transcriptSync.types';
import { CountryData } from '../types/adRequestStore.types';
import { getRandomVibrantColor } from '../helpers/utils';

interface AdData {
    index: number;
    musicAudioSrc: "pending" | "error" | string | null;
    nonMusicAudioSrc: "pending" | "error" | string | null;
    transcriptSents: "pending" | "error" | Sentence[] | null;
    englishTranscriptSents: string[] | null;
    insights: "pending" | "error" | Insight[] | null;
    location: string | null;
    status: "pending" | "done";
    theme: string | null;
}

interface AdDataState {
    ads: AdData[];
    activeIndex: number | null;

    setAds: (ads: AdData[] | ((prev: AdData[]) => AdData[])) => void
    appendAd: (ad: AdData) => void;
    setActiveIndex: (index: number) => void;
    getActiveAd: () => AdData | null;
    hasAdWithAudio: (index: number) => boolean;
    getAdLoadingState: (index: number) => boolean;
    getAdErrorState: (index: number) => boolean;
    getAvailableAudioSources: (index: number) => {
        musicAvailable: boolean;
        nonMusicAvailable: boolean;
        hasAnyAudio: boolean;
    };
    updateAd: (updatedAd: AdData) => void;
    populateAds: (data: CountryData[]) => void;
    failAllPendingRequests: () => void;
    nullifyAllPendingRequests: () => void;
}

const useAdData = create<AdDataState>((set, get) => ({
    ads: [],
    theme: "#8B5CF6",
    activeIndex: null,

    setAds: (adsOrUpdater) =>
        set((state) => ({
            ads:
                typeof adsOrUpdater === "function"
                    ? (adsOrUpdater as (prev: AdData[]) => AdData[])(state.ads)
                    : adsOrUpdater
        })),
    appendAd: (ad) => {
        const currentAds = get().ads
        get().setAds([...currentAds, ad])
    },
    setActiveIndex: (index) => set({ activeIndex: index }),
    getActiveAd: () => {
        const { ads, activeIndex } = get();
        if (activeIndex === null || activeIndex < 0 || activeIndex >= ads.length) return null;
        const foundAd = ads.find(ad => ad.index === activeIndex);
        return foundAd ?? null;
    },
    hasAdWithAudio: (index: number) => {
        const { ads } = get();
        const ad = ads.find(ad => ad.index === index);
        
        if (!ad) return false;
        
        const hasMusicAudio = Boolean(ad.musicAudioSrc && 
                                    ad.musicAudioSrc !== "pending" && 
                                    ad.musicAudioSrc !== "error");
        
        const hasNonMusicAudio = Boolean(ad.nonMusicAudioSrc && 
                                        ad.nonMusicAudioSrc !== "pending" && 
                                        ad.nonMusicAudioSrc !== "error");
        
        return hasMusicAudio || hasNonMusicAudio;
    },
    
    getAdLoadingState: (index: number) => {
        const { ads } = get();
        const ad = ads.find(ad => ad.index === index);
        
        if (!ad) return false;
        
        const musicLoading = ad.musicAudioSrc === "pending";
        const nonMusicLoading = ad.nonMusicAudioSrc === "pending";
        const musicNull = ad.musicAudioSrc === null;
        const nonMusicNull = ad.nonMusicAudioSrc === null;
        
        // Show loading if both are loading, or one is null and the other is loading
        return (musicLoading && nonMusicLoading) || 
               (musicNull && nonMusicLoading) || 
               (nonMusicNull && musicLoading);
    },
    
    getAdErrorState: (index: number) => {
        const { ads } = get();
        const ad = ads.find(ad => ad.index === index);
        
        if (!ad) return false;
        
        const musicError = ad.musicAudioSrc === "error";
        const nonMusicError = ad.nonMusicAudioSrc === "error";
        const musicNull = ad.musicAudioSrc === null;
        const nonMusicNull = ad.nonMusicAudioSrc === null;
        
        // Show error if both are errors, or one is null and the other is error
        return (musicError && nonMusicError) || 
               (musicNull && nonMusicError) || 
               (nonMusicNull && musicError);
    },
    
    getAvailableAudioSources: (index: number) => {
        const { ads } = get();
        const ad = ads.find(ad => ad.index === index);
        
        if (!ad) return { musicAvailable: false, nonMusicAvailable: false, hasAnyAudio: false };
        
        const musicAvailable = Boolean(ad.musicAudioSrc && 
                                     ad.musicAudioSrc !== "pending" && 
                                     ad.musicAudioSrc !== "error");
        
        const nonMusicAvailable = Boolean(ad.nonMusicAudioSrc && 
                                        ad.nonMusicAudioSrc !== "pending" && 
                                        ad.nonMusicAudioSrc !== "error");
        
        return {
            musicAvailable,
            nonMusicAvailable,
            hasAnyAudio: musicAvailable || nonMusicAvailable
        };
    },

    updateAd: (updatedAd: AdData) => {
        const { ads } = get();
        const oldAd = ads.find(ad => ad.index === updatedAd.index);
        
        console.log('📝 [adDataStore] updateAd called', {
            index: updatedAd.index,
            oldMusicSrc: oldAd?.musicAudioSrc,
            newMusicSrc: updatedAd.musicAudioSrc,
            oldNonMusicSrc: oldAd?.nonMusicAudioSrc,
            newNonMusicSrc: updatedAd.nonMusicAudioSrc,
            musicChanged: oldAd?.musicAudioSrc !== updatedAd.musicAudioSrc,
            nonMusicChanged: oldAd?.nonMusicAudioSrc !== updatedAd.nonMusicAudioSrc
        });
        
        const updatedAds = ads.map(ad => 
            ad.index === updatedAd.index ? updatedAd : ad
        );
        set({ ads: updatedAds });
    },

    populateAds: (data) => {
        data.forEach((country, index) => {
            get().appendAd({
                index: index,
                transcriptSents: "pending",
                englishTranscriptSents: null,
                insights: "pending",
                musicAudioSrc: "pending",
                nonMusicAudioSrc: "pending",
                location: country.name,
                status: "pending",
                theme: getRandomVibrantColor()
            })
        })
    },

    failAllPendingRequests: () => {
        const { ads } = get();
        const updatedAds = ads.map(ad => ({
            ...ad,
            musicAudioSrc: ad.musicAudioSrc === "pending" ? "error" : ad.musicAudioSrc,
            nonMusicAudioSrc: ad.nonMusicAudioSrc === "pending" ? "error" : ad.nonMusicAudioSrc,
            transcriptSents: ad.transcriptSents === "pending" ? "error" : ad.transcriptSents,
            insights: ad.insights === "pending" ? "error" : ad.insights,
            status: ad.status === "pending" ? "done" : ad.status
        }));
        set({ ads: updatedAds });
    },

    nullifyAllPendingRequests: () => {
        const { ads } = get();
        const updatedAds = ads.map(ad => ({
            ...ad,
            musicAudioSrc: ad.musicAudioSrc === "pending" ? null : ad.musicAudioSrc,
            nonMusicAudioSrc: ad.nonMusicAudioSrc === "pending" ? null : ad.nonMusicAudioSrc,
            transcriptSents: ad.transcriptSents === "pending" ? null : ad.transcriptSents,
            insights: ad.insights === "pending" ? null : ad.insights,
            status: ad.status === "pending" ? "done" : ad.status
        }));
        set({ ads: updatedAds });
    }
}))

export default useAdData