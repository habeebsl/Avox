'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import useAudioStore from '../store/audioStore';
import styles from './TranscriptSync.module.css';
import ThoughtBubbleTooltip from './ThoughtBubble';
import { Sentence, Insight } from "../types/transcriptSync.types";
import { mapInsightsToSentences } from '../helpers/utils';
import useAdData from '../store/adDataStore';
import { LoadingState, ErrorState, NullState } from './states/transcriptStates';

interface TranscriptSyncProps {
  className?: string;
  showTimestamps?: boolean;
  autoScroll?: boolean;
}

type LanguageOption = 'default' | 'english';

function processAdData(data: any) {
  if (data === "pending" || data === "error" || !data) return
  return data
}

const TranscriptSync: React.FC<TranscriptSyncProps> = ({
  className = '',
  showTimestamps = false,
  autoScroll = true,
}) => {
  const { currentTime, seekTo, isPlaying } = useAudioStore();
  const [currentSentenceIndex, setCurrentSentenceIndex] = useState<number>(-1);
  const [hoveredSentence, setHoveredSentence] = useState<number>(-1);
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageOption>('default');
  
  const { getActiveAd } = useAdData()
  const currentAd = getActiveAd()
  const theme = currentAd?.theme ?? "#008000"
  const sentences = currentAd?.transcriptSents
  const englishSentences = currentAd?.englishTranscriptSents
  const insights = currentAd?.insights

  const isLoading = sentences === "pending" || insights === "pending";
  const hasError = sentences === "error" || insights === "error";
  const isNull = sentences === null || insights === null || !currentAd;

  // Check if English transcript is available
  const hasEnglishTranscript = englishSentences !== null && englishSentences !== undefined;
  
  // Determine which version is English (the one that should get insights)
  const englishVersion: LanguageOption = hasEnglishTranscript ? 'english' : 'default';
  
  // Set initial language to whichever one is English
  useEffect(() => {
    setSelectedLanguage(englishVersion);
  }, [englishVersion]);
  
  // Reset to English version if availability changes
  useEffect(() => {
    if (!hasEnglishTranscript && selectedLanguage === 'english') {
      setSelectedLanguage('default');
    }
  }, [hasEnglishTranscript, selectedLanguage]);

  const processedSentences = useMemo(() => {
    const processedDefaultSentences = processAdData(sentences);
    const processedEnglishSentences = processAdData(englishSentences);
    const processedInsights = processAdData(insights);
    
    if (!processedDefaultSentences) {
      return [];
    }

    let finalSentences: Sentence[];
    let shouldApplyInsights = false;

    if (selectedLanguage === 'english' && processedEnglishSentences) {
      // Create English sentences with timing from default sentences
      finalSentences = processedDefaultSentences.map((defaultSent: Sentence, index: number) => ({
        ...defaultSent,
        text: processedEnglishSentences[index] || defaultSent.text
      }));
      shouldApplyInsights = true; // This is the English version
    } else {
      // Use default sentences
      finalSentences = processedDefaultSentences;
      // Apply insights to default only if this is the English version
      shouldApplyInsights = englishVersion === 'default';
    }

    // Apply insights if this is the English version
    if (shouldApplyInsights && processedInsights) {
      return mapInsightsToSentences(finalSentences, processedInsights);
    }
    
    return finalSentences;
  }, [sentences, englishSentences, insights, selectedLanguage, englishVersion]);

  // Refs for auto-scrolling
  const containerRef = React.useRef<HTMLDivElement>(null);
  const activeSentenceRef = React.useRef<HTMLDivElement>(null);

  // Find the current active sentence based on audio time
  useEffect(() => {
    const activeIndex = processAdData(sentences)?.findIndex((sentence: Sentence) => 
      currentTime >= sentence.start && currentTime < sentence.end
    ) ?? -1;
    setCurrentSentenceIndex(activeIndex);
  }, [currentTime, sentences]);

  // Auto-scroll to active sentence
  useEffect(() => {
    if (autoScroll && currentSentenceIndex >= 0 && activeSentenceRef.current && containerRef.current) {
      const container = containerRef.current;
      const activeElement = activeSentenceRef.current;
      
      const containerRect = container.getBoundingClientRect();
      const activeRect = activeElement.getBoundingClientRect();
      
      // Check if the active sentence is out of view
      const isAboveView = activeRect.top < containerRect.top;
      const isBelowView = activeRect.bottom > containerRect.bottom;
      
      if (isAboveView || isBelowView) {
        activeElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    }
  }, [currentSentenceIndex, autoScroll]);

  const handleSentenceClick = useCallback((sentence: Sentence) => {
    seekTo(sentence.start);
  }, [seekTo]);

  const handleLanguageChange = (language: LanguageOption) => {
    if (language === 'english' && !hasEnglishTranscript) return;
    setSelectedLanguage(language);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const LocationIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
    </svg>
  );

  const LanguageIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
    </svg>
  );

  const renderTextWithInsights = (text: string, insights: any[] = []) => {
    if (!insights || insights.length === 0) {
      return <span>{text}</span>;
    }

    const parts = [];
    let lastIndex = 0;

    const sortedInsights = insights.sort((a, b) => a.startChar - b.startChar);

    sortedInsights.forEach((insight, index) => {
      if (insight.startChar > lastIndex) {
        parts.push(
          <span key={`text-${index}`}>
            {text.substring(lastIndex, insight.startChar)}
          </span>
        );
      }

      const insightText = text.substring(insight.startChar, insight.endChar);
      parts.push(
        <ThoughtBubbleTooltip 
          key={`insight-${index}`} 
          text={insight.explanation}
        >
          <span 
            className={styles.insightHighlight}
            style={{
              background: `${theme}33`,
              borderColor: `${theme}4D`,
            }}
          >
            {insightText}
          </span>
        </ThoughtBubbleTooltip>
      );

      lastIndex = insight.endChar;
    });

    if (lastIndex < text.length) {
      parts.push(
        <span key="text-end">
          {text.substring(lastIndex)}
        </span>
      );
    }

    return <span>{parts}</span>;
  };

  return (
    <div className={`${styles.container} ${className}`} ref={containerRef}>
      <div className={styles.header}>
        <div className={styles.languageInfo}>
          <div className={styles.location}>
            <LocationIcon />
            <span>{currentAd?.location}</span>
          </div>
          
          <div className={styles.languageSelector}>
            <LanguageIcon />
            <select
              value={selectedLanguage}
              onChange={(e) => handleLanguageChange(e.target.value as LanguageOption)}
              className={styles.languageSelect}
              disabled={!hasEnglishTranscript}
            >
              <option value="default">Default</option>
              <option value="english">English</option>
            </select>
          </div>
        </div>
        
        <div className={styles.playingStatus}>
          {isPlaying && (
            <div className={styles.playingIndicator}>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
            </div>
          )}
        </div>
      </div>
      
      <div className={styles.transcript}>
        {isLoading && <LoadingState theme={theme} />}
        {hasError && <ErrorState theme={theme} showRetry={false} />}
        {isNull && !isLoading && !hasError && <NullState theme={theme} />}
        {(!isLoading && !hasError && !isNull && processedSentences?.map((sentence, index) => (
          <div
            key={index}
            ref={index === currentSentenceIndex ? activeSentenceRef : null}
            className={`${styles.sentence} ${
              index === currentSentenceIndex ? styles.active : ''
            }`}
            onClick={() => handleSentenceClick(sentence)}
            onMouseEnter={() => setHoveredSentence(index)}
            onMouseLeave={() => setHoveredSentence(-1)}
          >
            <div className={styles.sentenceContent}>
              <span className={styles.text}>
                {renderTextWithInsights(sentence.text, (sentence as any).insights || [])}
              </span>
            </div>
            
            {showTimestamps && (
              <div className={styles.timestamp}>
                {formatTime(sentence.start)}
              </div>
            )}
          </div>
        ))) ?? []}
      </div>
    </div>
  );
};

export default TranscriptSync;