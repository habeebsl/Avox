import React from 'react';
import styles from './ErrorState.module.css';

interface ErrorStateProps {
  theme: string;
  title?: string;
  message?: string;
  onRetry?: () => void;
  showRetry?: boolean;
}

const ErrorState: React.FC<ErrorStateProps> = ({ 
  theme, 
  title = "Transcript Unavailable",
  message = "We couldn't load the transcript for this audio. This might be due to processing issues or network connectivity.",
  onRetry,
  showRetry = true
}) => {
  const ErrorIcon = () => (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM13 17h-2v-2h2v2zm0-4h-2V7h2v6z"/>
    </svg>
  );

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div className={styles.icon} style={{ color: theme }}>
          <ErrorIcon />
        </div>
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.message}>{message}</p>
        {showRetry && onRetry && (
          <button 
            className={styles.retryButton}
            style={{ 
              background: `linear-gradient(135deg, ${theme}20, ${theme}10)`,
              borderColor: `${theme}40`,
              color: theme
            }}
            onClick={onRetry}
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
};

export default ErrorState;