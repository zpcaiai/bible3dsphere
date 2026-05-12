'use client';

import { clsx } from 'clsx';
import { ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'gentle' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          // Base styles
          'inline-flex items-center justify-center gap-2 font-medium transition-all duration-200',
          'focus-ring rounded-sfds-sm disabled:opacity-50 disabled:cursor-not-allowed',
          
          // Variant styles
          variant === 'primary' && [
            'bg-sfds-accent-teal text-white',
            'hover:bg-sfds-accent-teal/90 hover:shadow-md',
            'active:scale-[0.98]',
          ],
          variant === 'secondary' && [
            'bg-sfds-bg-secondary text-sfds-text-primary border border-sfds-border',
            'hover:bg-sfds-border hover:shadow-sm',
            'active:scale-[0.98]',
          ],
          variant === 'gentle' && [
            'bg-sfds-accent-teal-light text-sfds-accent-teal',
            'hover:bg-sfds-accent-teal/10',
            'active:scale-[0.98]',
          ],
          variant === 'ghost' && [
            'bg-transparent text-sfds-text-secondary',
            'hover:bg-sfds-bg-secondary hover:text-sfds-text-primary',
          ],
          
          // Size styles
          size === 'sm' && 'px-3 py-1.5 text-sm',
          size === 'md' && 'px-4 py-2.5 text-[15px]',
          size === 'lg' && 'px-6 py-3.5 text-base',
          
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
