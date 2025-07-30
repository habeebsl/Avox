import { create } from 'zustand';

export type NotificationType = 'loading' | 'ready' | 'error' | 'celebration' | 'batch';
export type NotificationPriority = 'immediate' | 'batch' | 'silent';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  trackIndex?: number;
  timestamp: number;
  duration?: number;
}

interface BatchedUpdate {
  type: 'ready' | 'error';
  trackIndexes: number[];
  timestamp: number;
}

interface NotificationState {
  notifications: Notification[];
  activeTrackIndex: number | null;
  batchedUpdates: BatchedUpdate[];
  batchTimer: NodeJS.Timeout | null;

  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  setActiveTrack: (index: number | null) => void;
  handleTrackUpdate: (trackIndex: number, type: 'loading' | 'ready' | 'error') => void;
  addToBatch: (trackIndex: number, type: 'ready' | 'error') => void;
  processBatchedUpdates: () => void;
  clearAllNotifications: () => void;
}

const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  activeTrackIndex: null,
  batchedUpdates: [],
  batchTimer: null,

  addNotification: (notification) => {
    const id = `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp: Date.now(),
      duration: notification.duration || 4000,
    };

    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));

    // Auto-remove after duration
    setTimeout(() => {
      get().removeNotification(id);
    }, newNotification.duration);
  },

  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter(n => n.id !== id),
    }));
  },

  setActiveTrack: (index) => {
    set({ activeTrackIndex: index });
  },

  handleTrackUpdate: (trackIndex, type) => {
    const { activeTrackIndex, batchTimer } = get();
    const isActiveTrack = activeTrackIndex === trackIndex;

    // Strategy implementation
    if (isActiveTrack) {
      get().addNotification(createActiveTrackNotification(trackIndex, type));
    } else {
      if (type === 'error') {
        get().addNotification(createErrorNotification(trackIndex));
      } else if (type === 'ready') {
        get().addToBatch(trackIndex, 'ready');
      }
    }
  },

  addToBatch: (trackIndex: number, type: 'ready' | 'error') => {
    const { batchedUpdates, batchTimer } = get();
    
    // Add to batch
    const existingBatch = batchedUpdates.find(b => b.type === type);
    if (existingBatch) {
      existingBatch.trackIndexes.push(trackIndex);
      existingBatch.timestamp = Date.now();
    } else {
      set((state) => ({
        batchedUpdates: [...state.batchedUpdates, {
          type,
          trackIndexes: [trackIndex],
          timestamp: Date.now(),
        }],
      }));
    }

    if (batchTimer) {
      clearTimeout(batchTimer);
    }

    const newTimer = setTimeout(() => {
      get().processBatchedUpdates();
    }, 5000);

    set({ batchTimer: newTimer });
  },

  processBatchedUpdates: () => {
    const { batchedUpdates } = get();
    
    batchedUpdates.forEach(batch => {
      if (batch.trackIndexes.length > 0) {
        get().addNotification(createBatchNotification(batch));
      }
    });

    set({ batchedUpdates: [], batchTimer: null });
  },

  clearAllNotifications: () => {
    const { batchTimer } = get();
    if (batchTimer) {
      clearTimeout(batchTimer);
    }
    set({ notifications: [], batchedUpdates: [], batchTimer: null });
  },
}));

// Helper functions for creating notifications
function createActiveTrackNotification(
  trackIndex: number, 
  type: string
): Omit<Notification, 'id' | 'timestamp'> {

  const baseTrack = `Track ${trackIndex + 1}`;
  
  switch (type) {
    case 'loading':
      return {
        type: 'loading',
        title: 'Cooking your audio ad...',
        message: `${baseTrack} is being generated`,
        trackIndex,
        duration: 3000,
      };
    case 'ready':
      return {
        type: 'ready',
        title: '🔥 Track ready!',
        message: `${baseTrack} is ready to play`,
        trackIndex,
        duration: 3000,
      };
    case 'error':
      return {
        type: 'error',
        title: 'Generation failed',
        message: `${baseTrack} encountered an error`,
        trackIndex,
        duration: 6000,
      };
    default:
      return {
        type: 'ready',
        title: 'Update',
        message: `${baseTrack} updated`,
        trackIndex,
      };
  }
}

function createErrorNotification(trackIndex: number): Omit<Notification, 'id' | 'timestamp'> {
  return {
    type: 'error',
    title: 'Track failed',
    message: `Track ${trackIndex + 1} needs attention`,
    trackIndex,
    duration: 8000
  };
}

function createBatchNotification(batch: BatchedUpdate): Omit<Notification, 'id' | 'timestamp'> {
  const count = batch.trackIndexes.length;
  const trackList = batch.trackIndexes.map(i => i + 1).join(', ');
  
  if (batch.type === 'ready') {
    return {
      type: 'batch',
      title: `🎉 ${count} track${count > 1 ? 's' : ''} ready!`,
      message: count > 3 ? `${count} more tracks completed` : `Tracks ${trackList} ready to play`,
      duration: 4000,
    };
  } else {
    return {
      type: 'batch',
      title: `${count} track${count > 1 ? 's' : ''} failed`,
      message: `Tracks ${trackList} need attention`,
      duration: 6000,
    };
  }
}

export default useNotificationStore;