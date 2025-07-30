import React from 'react';
import styles from './LoadingState.module.css';

interface LoadingStateProps {
  theme: string;
  message?: string;
}

const LoadingState: React.FC<LoadingStateProps> = ({ 
  theme, 
  message = "Generating transcript" 
}) => {
  return (
    <div className={styles.container}>
      <div className={styles.animation}>
        <div className={styles.waveContainer}>
          {[...Array(5)].map((_, i) => (
            <div 
              key={i}
              className={styles.waveBar}
              style={{ 
                animationDelay: `${i * 0.1}s`,
                background: `linear-gradient(45deg, ${theme}80, ${theme}40)`
              }}
            />
          ))}
        </div>
        <div className={styles.text}>
          <span>{message}</span>
          <div className={styles.dots}>
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoadingState;