'use client';

import React, { useEffect, useState } from 'react';
import { X, AlertCircle, CheckCircle, Loader, Zap } from 'lucide-react';
import useNotificationStore, { Notification } from '../store/notificationStore';

interface ToastProps {
  notification: Notification;
}

const Toast: React.FC<ToastProps> = ({ notification }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const { removeNotification } = useNotificationStore();

  useEffect(() => {
    setTimeout(() => setIsVisible(true), 50);
  }, []);

  const handleClose = () => {
    setIsLeaving(true);
    setTimeout(() => {
      removeNotification(notification.id);
    }, 300);
  };

  const getIcon = () => {
    switch (notification.type) {
      case 'loading':
        return <Loader className="w-5 h-5 animate-spin text-blue-400" />;
      case 'ready':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'celebration':
        return <Zap className="w-5 h-5 text-yellow-400" />;
      case 'batch':
        return <CheckCircle className="w-5 h-5 text-purple-400" />;
      default:
        return null;
    }
  };

  const getColorScheme = () => {
    switch (notification.type) {
      case 'loading':
        return 'border-blue-500/50 bg-blue-500/10';
      case 'ready':
        return 'border-green-500/50 bg-green-500/10';
      case 'error':
        return 'border-red-500/50 bg-red-500/10';
      case 'celebration':
        return 'border-yellow-500/50 bg-yellow-500/10';
      case 'batch':
        return 'border-purple-500/50 bg-purple-500/10';
      default:
        return 'border-white/20 bg-white/10';
    }
  };

  return (
    <div
      className={`
        transform transition-all duration-300 ease-out
        ${isVisible && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
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
              {notification.title}
            </h4>
            <button
              onClick={handleClose}
              className="flex-shrink-0 text-white/60 hover:text-white/80 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <p className="text-white/80 text-xs mt-1 leading-relaxed">
            {notification.message}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Toast;