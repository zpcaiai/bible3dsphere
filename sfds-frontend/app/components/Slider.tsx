'use client';

import { useState } from 'react';

interface SliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  lowLabel?: string;
  highLabel?: string;
  inverse?: boolean;
}

export function Slider({
  label,
  value,
  onChange,
  min = 1,
  max = 10,
  lowLabel,
  highLabel,
  inverse = false,
}: SliderProps) {
  const [isDragging, setIsDragging] = useState(false);

  const getColor = (val: number) => {
    if (inverse) {
      if (val <= 3) return '#5a9a8f'; // teal - good
      if (val <= 6) return '#8fa872'; // sage - moderate
      return '#c4a77d'; // warm - concerning
    }
    if (val >= 7) return '#5a9a8f';
    if (val >= 4) return '#8fa872';
    return '#c4a77d';
  };

  const color = getColor(value);

  return (
    <div className="mb-6">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-sfds-text-primary">{label}</span>
        <span 
          className="text-sm font-semibold min-w-[24px] text-right"
          style={{ color }}
        >
          {value}
        </span>
      </div>
      
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value))}
          onMouseDown={() => setIsDragging(true)}
          onMouseUp={() => setIsDragging(false)}
          onTouchStart={() => setIsDragging(true)}
          onTouchEnd={() => setIsDragging(false)}
          className="w-full h-1.5 bg-sfds-border rounded-full appearance-none cursor-pointer focus-ring"
          style={{
            background: `linear-gradient(to right, ${color} 0%, ${color} ${((value - min) / (max - min)) * 100}%, #e8e6e3 ${((value - min) / (max - min)) * 100}%, #e8e6e3 100%)`,
          }}
        />
        <style jsx>{`
          input[type='range']::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            background: white;
            border: 3px solid ${color};
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.1s;
          }
          input[type='range']::-webkit-slider-thumb:hover {
            transform: scale(1.1);
          }
          input[type='range']::-moz-range-thumb {
            width: 20px;
            height: 20px;
            background: white;
            border: 3px solid ${color};
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          }
        `}</style>
      </div>
      
      {(lowLabel || highLabel) && (
        <div className="flex justify-between mt-1">
          {lowLabel && (
            <span className="text-xs text-sfds-text-muted">{lowLabel}</span>
          )}
          {highLabel && (
            <span className="text-xs text-sfds-text-muted">{highLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
