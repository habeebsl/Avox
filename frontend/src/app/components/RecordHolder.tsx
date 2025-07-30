'use client'

import React, { useState, useRef, useEffect } from 'react';
import useAdData from '../store/adDataStore';
import { AdCube } from './AdCube';
import styles from './RecordHolder.module.css';

interface RecordHolderProps {
  className?: string;
}

export const RecordHolder: React.FC<RecordHolderProps> = ({ className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const { ads } = useAdData()
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleOpen = () => {
    if (isAnimating) return;
    setIsAnimating(true);
    setIsOpen(!isOpen);
    
    // Reset animation state after animation completes
    setTimeout(() => {
      setIsAnimating(false);
    }, 300);
  };

  return (
    <div className={`${styles.recordHolder} ${className}`} ref={containerRef}>
      {/* Main Record Holder Button */}
      <div 
        className={`${styles.holderButton} ${isOpen ? styles.open : ''}`}
        onClick={toggleOpen}
      >
        <div className={styles.holderInner}>
          <div className={styles.recordStack}>
            <div className={styles.record}></div>
            <div className={styles.record}></div>
            <div className={styles.record}></div>
          </div>
          
          {/* Vinyl record icon */}
          <div className={styles.vinylIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <circle cx="12" cy="12" r="6" fill="none" stroke="currentColor" strokeWidth="1"/>
              <circle cx="12" cy="12" r="2" fill="currentColor"/>
              <circle cx="12" cy="12" r="0.5" fill="none" stroke="currentColor" strokeWidth="0.5"/>
            </svg>
          </div>
          
          {/* Arrow indicator - now points down when closed */}
          <div className={`${styles.arrow} ${isOpen ? styles.rotated : ''}`}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 10l5 5 5-5z"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Sliding Container */}
      <div className={`${styles.slidingContainer} ${isOpen ? styles.visible : ''}`}>
        <div className={styles.adsContainer}>
          <div className={styles.adLabel}>
            <span>Audio Tracks</span>
            <div className={styles.trackCount}>{ads.length}</div>
          </div>
          
          <div className={styles.adsList}>
            {
              ads.map(ad => (
                <AdCube 
                  key={ad.index}
                  index={ad.index}
                  theme={ad.theme ?? "#008000"}
                />
              ))
            }
          </div>
        </div>
      </div>

      {/* Backdrop */}
      {isOpen && (
        <div 
          className={styles.backdrop}
          onClick={toggleOpen}
        />
      )}
    </div>
  );
};