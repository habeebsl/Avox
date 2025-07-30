'use client';

import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import useAdData from '../store/adDataStore';

interface ThoughtBubbleTooltipProps {
  text: string;
  children: React.ReactNode;
  className?: string;
  maxWidth?: number;
}

const ThoughtBubbleTooltip: React.FC<ThoughtBubbleTooltipProps> = ({
  text,
  children,
  className = '',
  maxWidth = 320,
}) => {
  const { getActiveAd } = useAdData()
  const activeAd = getActiveAd()
  const theme = activeAd?.theme ?? "#008000"
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState<'top' | 'bottom' | 'left' | 'right'>('top');
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
  const [mounted, setMounted] = useState(false);
  const [isPositioned, setIsPositioned] = useState(false);
  
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const calculatePosition = () => {
    if (!triggerRef.current || !isVisible) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight
    };

    // Estimate tooltip dimensions based on content
    const estimatedWidth = Math.min(maxWidth, Math.max(120, text.length * 8));
    const estimatedHeight = Math.max(60, Math.ceil(text.length / 40) * 24 + 40);

    const spacing = 12;
    let bestPosition: 'top' | 'bottom' | 'left' | 'right' = 'top';
    let style: React.CSSProperties = {};

    // Calculate available space in each direction
    const spaceTop = triggerRect.top;
    const spaceBottom = viewport.height - triggerRect.bottom;
    const spaceLeft = triggerRect.left;
    const spaceRight = viewport.width - triggerRect.right;

    // Determine best position based on available space
    if (spaceTop >= estimatedHeight + spacing) {
      bestPosition = 'top';
    } else if (spaceBottom >= estimatedHeight + spacing) {
      bestPosition = 'bottom';
    } else if (spaceRight >= estimatedWidth + spacing) {
      bestPosition = 'right';
    } else if (spaceLeft >= estimatedWidth + spacing) {
      bestPosition = 'left';
    } else {
      const maxSpace = Math.max(spaceTop, spaceBottom, spaceLeft, spaceRight);
      if (maxSpace === spaceTop) bestPosition = 'top';
      else if (maxSpace === spaceBottom) bestPosition = 'bottom';
      else if (maxSpace === spaceRight) bestPosition = 'right';
      else bestPosition = 'left';
    }

    // Calculate positioning styles using viewport coordinates
    switch (bestPosition) {
      case 'top':
        style = {
          position: 'fixed',
          top: triggerRect.top - spacing,
          left: triggerRect.left + (triggerRect.width / 2),
          transform: 'translate(-50%, -100%)',
          zIndex: 50
        };
        
        const leftEdgeCheck = triggerRect.left + (triggerRect.width / 2) - (estimatedWidth / 2);
        const rightEdgeCheck = triggerRect.left + (triggerRect.width / 2) + (estimatedWidth / 2);
        
        if (leftEdgeCheck < 10) {
          style.left = triggerRect.left;
          style.transform = 'translate(0%, -100%)';
        } else if (rightEdgeCheck > viewport.width - 10) {
          style.left = triggerRect.right;
          style.transform = 'translate(-100%, -100%)';
        }
        break;
      case 'bottom':
        style = {
          position: 'fixed',
          top: triggerRect.bottom + spacing,
          left: triggerRect.left + (triggerRect.width / 2),
          transform: 'translate(-50%, 0%)',
          zIndex: 50
        };

        const leftEdgeCheckBottom = triggerRect.left + (triggerRect.width / 2) - (estimatedWidth / 2);
        const rightEdgeCheckBottom = triggerRect.left + (triggerRect.width / 2) + (estimatedWidth / 2);
        
        if (leftEdgeCheckBottom < 10) {
          style.left = triggerRect.left;
          style.transform = 'translate(0%, 0%)';
        } else if (rightEdgeCheckBottom > viewport.width - 10) {
          style.left = triggerRect.right;
          style.transform = 'translate(-100%, 0%)';
        }
        break;
      case 'left':
        style = {
          position: 'fixed',
          top: triggerRect.top + (triggerRect.height / 2),
          left: triggerRect.left - spacing,
          transform: 'translate(-100%, -50%)',
          zIndex: 50
        };
        break;
      case 'right':
        style = {
          position: 'fixed',
          top: triggerRect.top + (triggerRect.height / 2),
          left: triggerRect.right + spacing,
          transform: 'translate(0%, -50%)',
          zIndex: 50
        };
        break;
    }

    setPosition(bestPosition);
    setTooltipStyle(style);
    setIsPositioned(true);
  };

  useEffect(() => {
    if (isVisible) {
      setIsPositioned(false);
      calculatePosition();
    }
  }, [isVisible, text, maxWidth]);

  useEffect(() => {
    if (isVisible) {
      const handleResize = () => {
        setIsPositioned(false);
        calculatePosition();
      };
      const handleScroll = () => {
        setIsPositioned(false);
        calculatePosition();
      };
      
      window.addEventListener('resize', handleResize);
      window.addEventListener('scroll', handleScroll);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        window.removeEventListener('scroll', handleScroll);
      };
    }
  }, [isVisible]);


  const tooltipContent = isVisible && mounted && isPositioned ? (
    <div
      ref={tooltipRef}
      className="pointer-events-none"
      style={tooltipStyle}
    >
      <div 
        className="relative bg-[#000000f6] rounded-xl px-5 py-4 shadow-2xl shadow-black/50"
        style={{ 
          maxWidth: `${maxWidth}px`,
          minWidth: '120px',
          borderWidth: '1px',
          borderStyle: 'solid',
          borderColor: `${theme}CC`
        }}
      >
        <p className="text-gray-100 text-base font-medium italic whitespace-pre-wrap leading-relaxed tracking-wide drop-shadow-sm">
          {text}
        </p>
      </div>
    </div>
  ) : null;

  return (
    <>
      <div
        ref={triggerRef}
        className={`relative inline ${className}`}
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        {children}
      </div>
      
      {mounted && tooltipContent && createPortal(tooltipContent, document.body)}
    </>
  );
};

export default ThoughtBubbleTooltip;