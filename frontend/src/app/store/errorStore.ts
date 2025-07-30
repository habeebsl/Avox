import { create } from 'zustand';

interface ErrorState {
    title: string;
    message: string;
    showError: boolean;

    setTitle: (title: string) => void;
    setMessage: (message: string) => void;
    setShowError: (data: boolean) => void;
}

const useError = create<ErrorState>((set, get) => ({
    title: '',
    message: '',
    showError: false,

    setTitle: (title) => set({ title: title }),
    setMessage: (message) => set({ message: message }),
    setShowError: (data) => set({ showError: data })
}))

export default useError;