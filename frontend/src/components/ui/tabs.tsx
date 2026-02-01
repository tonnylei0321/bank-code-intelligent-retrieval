import React, { useState } from 'react';

interface TabsProps {
  children: React.ReactNode;
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

interface TabsTriggerProps {
  children: React.ReactNode;
  value: string;
  className?: string;
}

interface TabsContentProps {
  children: React.ReactNode;
  value: string;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ 
  children, 
  defaultValue, 
  value: controlledValue, 
  onValueChange, 
  className = '' 
}) => {
  const [internalValue, setInternalValue] = useState(defaultValue || '');
  const value = controlledValue !== undefined ? controlledValue : internalValue;
  
  const handleValueChange = (newValue: string) => {
    if (controlledValue === undefined) {
      setInternalValue(newValue);
    }
    onValueChange?.(newValue);
  };
  
  return (
    <div className={className}>
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { 
            value, 
            onValueChange: handleValueChange 
          } as any);
        }
        return child;
      })}
    </div>
  );
};

export const TabsList: React.FC<TabsListProps & any> = ({ 
  children, 
  className = '', 
  value, 
  onValueChange 
}) => {
  return (
    <div className={`inline-flex h-10 items-center justify-center rounded-md bg-gray-100 p-1 text-gray-500 ${className}`}>
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { 
            value, 
            onValueChange 
          } as any);
        }
        return child;
      })}
    </div>
  );
};

export const TabsTrigger: React.FC<TabsTriggerProps & any> = ({ 
  children, 
  value: triggerValue, 
  className = '', 
  value, 
  onValueChange 
}) => {
  const isActive = value === triggerValue;
  
  return (
    <button
      type="button"
      onClick={() => onValueChange(triggerValue)}
      className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${
        isActive 
          ? 'bg-white text-gray-950 shadow-sm' 
          : 'text-gray-500 hover:text-gray-900'
      } ${className}`}
    >
      {children}
    </button>
  );
};

export const TabsContent: React.FC<TabsContentProps & any> = ({ 
  children, 
  value: contentValue, 
  className = '', 
  value 
}) => {
  if (value !== contentValue) return null;
  
  return (
    <div className={`mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${className}`}>
      {children}
    </div>
  );
};