'use client';

import React from 'react';
import useNotificationStore from '../store/notificationStore';
import Toast from './Toast';

const ToastContainer: React.FC = () => {
  const { notifications } = useNotificationStore();

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-h-screen overflow-hidden">
      {notifications.map((notification) => (
        <Toast key={notification.id} notification={notification} />
      ))}
    </div>
  );
};

export default ToastContainer;