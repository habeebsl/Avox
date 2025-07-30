'use client';

import React, { useEffect, useState } from 'react';
import { X, AlertCircle, AlertTriangle } from 'lucide-react';

interface ErrorNotificationProps {
  title: string;
  message: string;
  severity?: 'error' | 'warning';
  isVisible?: boolean;
  onClose?: () => void;
  autoClose?: boolean;
  autoCloseDelay?: number;
}

const ErrorNotification: React.FC<ErrorNotificationProps> = ({
  title,
  message,
  severity = 'error',
  isVisible = true,
  onClose,
  autoClose = false,
  autoCloseDelay = 5000,
}) => {
  const [showNotification, setShowNotification] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setTimeout(() => setShowNotification(true), 50);
    }
  }, [isVisible]);

  useEffect(() => {
    if (autoClose && isVisible && showNotification) {
      const timer = setTimeout(() => {
        handleClose();
      }, autoCloseDelay);

      return () => clearTimeout(timer);
    }
  }, [autoClose, autoCloseDelay, isVisible, showNotification]);

  const handleClose = () => {
    setIsLeaving(true);
    setTimeout(() => {
      setShowNotification(false);
      onClose?.();
    }, 300);
  };

  const getIcon = () => {
    switch (severity) {
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
      case 'error':
      default:
        return <AlertCircle className="w-5 h-5 text-red-400" />;
    }
  };

  const getColorScheme = () => {
    switch (severity) {
      case 'warning':
        return 'border-yellow-500/50 bg-yellow-500/10';
      case 'error':
      default:
        return 'border-red-500/50 bg-red-500/10';
    }
  };

  if (!isVisible && !showNotification) {
    return null;
  }

  return (
    <div
      className={`
        absolute bottom-15 right-3
        transform transition-all duration-300 ease-out
        ${showNotification && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        ${getColorScheme()}
        backdrop-blur-md border rounded-lg p-4 shadow-lg max-w-sm w-full
        group hover:scale-105
      `}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {getIcon()}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-white font-medium text-sm truncate">
              {title}
            </h4>
            <button
              onClick={handleClose}
              className="flex-shrink-0 text-white/60 hover:text-white/80 transition-colors"
              aria-label="Close notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <p className="text-white/80 text-xs mt-1 leading-relaxed">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ErrorNotification;