"use client";

import { useEffect, useState } from 'react';

interface ErrorIconProps {
  size?: number;
  className?: string;
}

export default function ErrorIcon({ size = 24, className = "" }: ErrorIconProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <div 
        className={`
          absolute inset-0 rounded-full border-2 border-red-500/30
          ${mounted ? 'animate-ping' : 'opacity-0'}
        `}
        style={{
          animationDuration: '1s',
          animationIterationCount: '3'
        }}
      />
      <div 
        className={`
          absolute inset-0 rounded-full border border-red-400/20
          ${mounted ? 'animate-pulse' : 'opacity-0'}
        `}
        style={{
          animationDelay: '0.2s',
          animationDuration: '1.5s',
          animationIterationCount: '2'
        }}
      />
      
      <div 
        className={`
          relative z-10 bg-red-500 rounded-full flex items-center justify-center
        `}
        style={{ 
          width: size, 
          height: size
        }}
      >
        <svg 
          width={size * 0.6} 
          height={size * 0.6} 
          viewBox="0 0 24 24" 
          fill="none"
          className="text-white"
        >
          <path 
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}