import React, { useState } from 'react';

interface SelectProps {
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
}

interface SelectTriggerProps {
  children: React.ReactNode;
  className?: string;
}

interface SelectContentProps {
  children: React.ReactNode;
}

interface SelectItemProps {
  children: React.ReactNode;
  value: string;
}

interface SelectValueProps {
  placeholder?: string;
}

export const Select: React.FC<SelectProps> = ({ children, value, onValueChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="relative">
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { 
            isOpen, 
            setIsOpen, 
            value, 
            onValueChange 
          } as any);
        }
        return child;
      })}
    </div>
  );
};

export const SelectTrigger: React.FC<SelectTriggerProps & any> = ({ 
  children, 
  className = '', 
  isOpen, 
  setIsOpen 
}) => {
  return (
    <button
      type="button"
      onClick={() => setIsOpen(!isOpen)}
      className={`flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    >
      {children}
      <svg className="h-4 w-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  );
};

export const SelectContent: React.FC<SelectContentProps & any> = ({ 
  children, 
  isOpen, 
  setIsOpen, 
  value, 
  onValueChange 
}) => {
  if (!isOpen) return null;
  
  return (
    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg">
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { 
            setIsOpen, 
            value, 
            onValueChange 
          } as any);
        }
        return child;
      })}
    </div>
  );
};

export const SelectItem: React.FC<SelectItemProps & any> = ({ 
  children, 
  value: itemValue, 
  setIsOpen, 
  value, 
  onValueChange 
}) => {
  return (
    <div
      className={`px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 ${value === itemValue ? 'bg-blue-50 text-blue-600' : ''}`}
      onClick={() => {
        onValueChange?.(itemValue);
        setIsOpen(false);
      }}
    >
      {children}
    </div>
  );
};

export const SelectValue: React.FC<SelectValueProps & any> = ({ 
  placeholder, 
  value 
}) => {
  return (
    <span className={value ? '' : 'text-gray-400'}>
      {value || placeholder}
    </span>
  );
};