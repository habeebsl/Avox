'use client';

import { useState, useEffect } from 'react';
import { ChevronDownIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { useAdRequest, ForecastType } from '@/app/store/adRequestStore';

interface Country {
  name: string;
  code: string;
}

interface Language {
  name: string;
  code: string;
}

const countries: Country[] = [
  { name: 'United States', code: 'US' },
  { name: 'United Kingdom', code: 'GB' },
  { name: 'Canada', code: 'CA' },
  { name: 'Australia', code: 'AU' },
  { name: 'Germany', code: 'DE' },
  { name: 'France', code: 'FR' },
  { name: 'Japan', code: 'JP' },
  { name: 'Brazil', code: 'BR' },
  { name: 'India', code: 'IN' },
  { name: 'China', code: 'CN' },
  { name: 'Nigeria', code: 'NG' }
];

const languages: Language[] = [
  { name: 'English', code: 'en' },
  { name: 'Spanish', code: 'es' },
  { name: 'French', code: 'fr' },
  { name: 'German', code: 'de' },
  { name: 'Italian', code: 'it' },
  { name: 'Portuguese', code: 'pt' },
  { name: 'Japanese', code: 'ja' },
  { name: 'Chinese', code: 'zh' },
  { name: 'Korean', code: 'ko' },
  { name: 'Hindi', code: 'hi' },
];

const VoiceSelectionForm = () => {
  const [voiceMode, setVoiceMode] = useState<'auto' | 'custom'>('auto');
  const [selectedCountries, setSelectedCountries] = useState<Country[]>([]);
  const [weatherDepth, setWeatherDepth] = useState<number>(0);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [isCountryDropdownOpen, setIsCountryDropdownOpen] = useState(false);
  const [isLanguageDropdownOpen, setIsLanguageDropdownOpen] = useState(false);
  const { 
    locations, 
    setLocations, 
    cloneLanguage,
    setCloneLanguage, 
    adType, 
    setAdType, 
    setForecastType,
    setDisableNextButton
  } = useAdRequest()

  const weatherOptions = [
    { value: 0, label: '0' },
    { value: 7, label: '7 days' },
    { value: 14, label: '14 days' },
  ];

  const handleCountrySelect = (country: Country) => {
    if (voiceMode === 'custom') {
      setSelectedCountries([country]);
    } else {
      if (selectedCountries.find(c => c.code === country.code)) {
        setSelectedCountries(selectedCountries.filter(c => c.code !== country.code));
      } else if (selectedCountries.length < 3) {
        setSelectedCountries([...selectedCountries, country]);
      }
    }
  };

  const removeCountry = (countryCode: string) => {
    setSelectedCountries(selectedCountries.filter(c => c.code !== countryCode));
  };

  const getWeatherDepthPosition = () => {
    if (weatherDepth === 0) return '0%';
    if (weatherDepth === 7) return '50%';
    if (weatherDepth === 14) return '100%';
    return '0%';
  };

  const handleSliderClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;
    const percentage = clickX / width;

    if (percentage <= 0.25) {
      setWeatherDepth(0);
    } else if (percentage <= 0.75) {
      setWeatherDepth(7);
    } else {
      setWeatherDepth(14);
    }
  };

  useEffect(() => {
    if (selectedLanguage) {
      setCloneLanguage(selectedLanguage)
    }

    if (voiceMode === "auto") {
      setAdType("default")
    } else {
      setAdType("custom")
    }

    setForecastType(weatherDepth as ForecastType)
    setLocations(selectedCountries)

    if (selectedCountries.length > 0) {
      // console.log(selectedCountries.length)
      if (adType === "default") {
        setDisableNextButton(false)
      } 
      
      if (adType === "custom") {
        if (cloneLanguage) {
          setDisableNextButton(false)
        } else {
          setDisableNextButton(true)
        }
      }
    } else {
      setDisableNextButton(true)
    }

  }, [voiceMode, selectedCountries, weatherDepth, selectedLanguage])


  const maxCountries = voiceMode === 'custom' ? 1 : 3;
  const isCountryLimitReached = selectedCountries.length >= maxCountries;

  return (
    <div className="bg-black min-h-screen w-full p-8 flex justify-center items-center">
      <div className="max-w-lg mx-auto flex-1">
        <div className="bg-black border border-gray-800 rounded-3xl p-8 shadow-2xl backdrop-blur-sm">
          
          {/* Voice Mode Selection */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-white text-lg font-semibold tracking-wide">Select Voice</h3>
              <div className="group relative">
                <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                  Choose between automatic or custom voice settings
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                </div>
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-2xl p-2 border border-gray-700">
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setVoiceMode('auto');
                    if (selectedCountries.length > 3) {
                      setSelectedCountries(selectedCountries.slice(0, 3));
                    }
                  }}
                  className={`flex-1 py-3 px-6 rounded-xl text-sm font-medium transition-all duration-300 ${
                    voiceMode === 'auto'
                      ? 'bg-white text-black shadow-lg scale-105'
                      : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
                  }`}
                >
                  Auto
                </button>
                <button
                  onClick={() => {
                    setVoiceMode('custom');
                    if (selectedCountries.length > 1) {
                      setSelectedCountries([selectedCountries[0]]);
                    }
                  }}
                  className={`flex-1 py-3 px-6 rounded-xl text-sm font-medium transition-all duration-300 ${
                    voiceMode === 'custom'
                      ? 'bg-white text-black shadow-lg scale-105'
                      : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
                  }`}
                >
                  Custom
                </button>
              </div>
            </div>
          </div>

          {/* Countries Selection */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-white text-lg font-semibold tracking-wide">Countries</h3>
                <div className="group relative">
                  <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                    {voiceMode === 'custom' ? 'Select one country for custom voice' : 'Select up to 3 countries for auto mode'}
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                  </div>
                </div>
              </div>
              
              {/* Selection Counter */}
              <div className={`text-sm font-medium px-3 py-1 rounded-full border transition-all duration-200 ${
                isCountryLimitReached 
                  ? 'text-orange-400 bg-orange-400/10 border-orange-400/30' 
                  : 'text-gray-400 bg-gray-800/50 border-gray-600'
              }`}>
                {selectedCountries.length}/{maxCountries}
              </div>
            </div>

            {/* Limit Notice */}
            <div className={`mb-4 text-sm transition-all duration-200 ${
              voiceMode === 'custom' 
                ? 'text-blue-400 bg-blue-400/10 border border-blue-400/20' 
                : 'text-green-400 bg-green-400/10 border border-green-400/20'
            } px-4 py-2 rounded-xl`}>
              {voiceMode === 'custom' 
                ? '🎯 Custom mode: Select exactly 1 country' 
                : '🌍 Auto mode: Select up to 3 countries'}
            </div>
            
            <div className="relative">
              <div
                onClick={() => setIsCountryDropdownOpen(!isCountryDropdownOpen)}
                className="bg-gray-800/30 border border-gray-600 rounded-2xl px-5 py-4 text-white cursor-pointer flex items-center justify-between hover:bg-gray-700/30 transition-all duration-200 hover:border-gray-500"
              >
                <span className="text-base">
                  {selectedCountries.length === 0
                    ? 'Select countries...'
                    : selectedCountries.length === 1
                    ? selectedCountries[0].name
                    : `${selectedCountries.length} countries selected`}
                </span>
                <ChevronDownIcon className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${isCountryDropdownOpen ? 'rotate-180' : ''}`} />
              </div>

              {isCountryDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-gray-800/95 backdrop-blur-md border border-gray-600 rounded-2xl max-h-56 overflow-y-auto z-30 shadow-2xl">
                  {countries.map((country) => {
                    const isSelected = selectedCountries.find(c => c.code === country.code);
                    const canSelect = !isSelected && !isCountryLimitReached;
                    const isDisabled = !isSelected && isCountryLimitReached;
                    
                    return (
                      <div
                        key={country.code}
                        onClick={() => canSelect || isSelected ? handleCountrySelect(country) : null}
                        className={`px-5 py-3 text-base cursor-pointer transition-all duration-200 first:rounded-t-2xl last:rounded-b-2xl ${
                          isSelected
                            ? 'bg-gray-600/50 border-l-4 border-white text-white' 
                            : isDisabled
                            ? 'text-gray-500 cursor-not-allowed opacity-50'
                            : 'text-white hover:bg-gray-700/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          {country.name}
                          {isDisabled && (
                            <span className="text-xs text-gray-500">
                              {voiceMode === 'custom' ? 'Max 1' : 'Max 3'}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Selected Countries Tags */}
            {selectedCountries.length > 0 && (
              <div className="flex flex-wrap gap-3 mt-4">
                {selectedCountries.map((country) => (
                  <div
                    key={country.code}
                    className="bg-gradient-to-r from-gray-700 to-gray-600 text-white text-sm px-4 py-2 rounded-full flex items-center gap-2 shadow-lg border border-gray-600"
                  >
                    {country.name}
                    <button
                      onClick={() => removeCountry(country.code)}
                      className="text-gray-300 hover:text-white hover:bg-gray-600 rounded-full w-5 h-5 flex items-center justify-center transition-all duration-200"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Limit reached warning */}
            {isCountryLimitReached && (
              <div className="mt-3 text-sm text-orange-400 bg-orange-400/10 border border-orange-400/20 px-4 py-2 rounded-xl">
                ⚠️ {voiceMode === 'custom' ? 'You can only select 1 country in custom mode' : 'Maximum of 3 countries reached'}
              </div>
            )}
          </div>

          {/* Language Selection (Custom Mode Only) */}
          {voiceMode === 'custom' && (
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-white text-lg font-semibold tracking-wide">Language</h3>
                <div className="group relative">
                  <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                    Select the language for custom voice
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                  </div>
                </div>
              </div>
              
              <div className="relative">
                <div
                  onClick={() => setIsLanguageDropdownOpen(!isLanguageDropdownOpen)}
                  className="bg-gray-800/30 border border-gray-600 rounded-2xl px-5 py-4 text-white cursor-pointer flex items-center justify-between hover:bg-gray-700/30 transition-all duration-200 hover:border-gray-500"
                >
                  <span className="text-base">
                    {selectedLanguage
                      ? languages.find(l => l.code === selectedLanguage)?.name
                      : 'Select language...'}
                  </span>
                  <ChevronDownIcon className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${isLanguageDropdownOpen ? 'rotate-180' : ''}`} />
                </div>

                {isLanguageDropdownOpen && (
                  <div className="absolute top-full left-0 right-0 mt-2 bg-gray-800/95 backdrop-blur-md border border-gray-600 rounded-2xl max-h-56 overflow-y-auto z-30 shadow-2xl">
                    {languages.map((language) => (
                      <div
                        key={language.code}
                        onClick={() => {
                          setSelectedLanguage(language.code);
                          setIsLanguageDropdownOpen(false);
                        }}
                        className={`px-5 py-3 text-base text-white cursor-pointer transition-all duration-200 first:rounded-t-2xl last:rounded-b-2xl ${
                          selectedLanguage === language.code 
                            ? 'bg-gray-600/50 border-l-4 border-white' 
                            : 'hover:bg-gray-700/50'
                        }`}
                      >
                        {language.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Weather Depth Slider */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-6">
              <h3 className="text-white text-lg font-semibold tracking-wide">Weather Depth</h3>
              <div className="group relative">
                <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                  Select weather forecast depth: current, 7 days, or 14 days
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="relative px-2">
                <div
                  className="h-3 bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 rounded-full cursor-pointer shadow-inner border border-gray-600"
                  onClick={handleSliderClick}
                >
                  <div
                    className="absolute top-1/2 transform w-7 h-7 bg-gradient-to-b from-white to-gray-200 rounded-full shadow-2xl border-2 border-gray-300 transition-all duration-300 hover:scale-110"
                    style={{ left: getWeatherDepthPosition(), transform: 'translateX(-50%) translateY(-50%)' }}
                  />
                </div>
              </div>
              
              <div className="flex justify-between px-2">
                {weatherOptions.map((option) => (
                  <button
                    key={option.value}
                    className={`text-sm font-medium transition-all duration-200 px-3 py-1 rounded-lg ${
                      weatherDepth === option.value 
                        ? 'text-white bg-gray-700/50 shadow-lg' 
                        : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/30'
                    }`}
                    onClick={() => setWeatherDepth(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default VoiceSelectionForm;