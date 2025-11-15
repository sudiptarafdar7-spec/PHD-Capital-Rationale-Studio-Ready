import React, { useState, useEffect, useRef } from 'react';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from './ui/command';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Input } from './ui/input';
import { API_ENDPOINTS, getAuthHeaders } from '../lib/api-config';
import { Check, Loader2 } from 'lucide-react';
import { cn } from './ui/utils';

interface Stock {
  name: string;
  symbol: string;
  securityId: string;
  exchange: string;
}

interface StockAutocompleteInputProps {
  value: string;
  onSelect: (stockName: string) => void;
  token: string;
  placeholder?: string;
  disabled?: boolean;
}

export function StockAutocompleteInput({
  value,
  onSelect,
  token,
  placeholder = 'Type to search stocks...',
  disabled = false,
}: StockAutocompleteInputProps) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [debouncedValue, setDebouncedValue] = useState(inputValue);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Debounce input value
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(inputValue);
    }, 300);

    return () => clearTimeout(timer);
  }, [inputValue]);

  // Fetch suggestions when debounced value changes
  useEffect(() => {
    if (!debouncedValue || debouncedValue.length < 2) {
      setSuggestions([]);
      return;
    }

    const fetchSuggestions = async () => {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      abortControllerRef.current = new AbortController();

      setLoading(true);

      try {
        const response = await fetch(API_ENDPOINTS.uploadedFiles.masterStocks(debouncedValue), {
          headers: getAuthHeaders(token),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error('Failed to fetch stocks');
        }

        const data = await response.json();
        setSuggestions(data.stocks || []);
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Error fetching stock suggestions:', error);
          setSuggestions([]);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchSuggestions();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [debouncedValue, token]);

  // Sync external value changes
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  const handleSelect = (stock: Stock) => {
    setInputValue(stock.name);
    onSelect(stock.name);
    setOpen(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    onSelect(newValue); // Update parent state immediately
    
    if (newValue.length >= 2) {
      setOpen(true);
    } else {
      setOpen(false);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <div className="relative">
          <Input
            value={inputValue}
            onChange={handleInputChange}
            onFocus={() => {
              if (inputValue.length >= 2 && suggestions.length > 0) {
                setOpen(true);
              }
            }}
            placeholder={placeholder}
            disabled={disabled}
            className="bg-background border-input"
          />
          {loading && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground animate-spin" />
          )}
        </div>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Command>
          <CommandList>
            {suggestions.length === 0 && !loading && debouncedValue.length >= 2 && (
              <CommandEmpty>No stocks found.</CommandEmpty>
            )}
            {suggestions.length > 0 && (
              <CommandGroup>
                {suggestions.map((stock, index) => (
                  <CommandItem
                    key={`${stock.securityId}-${index}`}
                    value={stock.name}
                    onSelect={() => handleSelect(stock)}
                    className="cursor-pointer"
                  >
                    <div className="flex items-center justify-between w-full">
                      <div className="flex flex-col">
                        <span className="font-medium">{stock.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {stock.symbol} • {stock.exchange}
                        </span>
                      </div>
                      {inputValue === stock.name && (
                        <Check className="w-4 h-4 text-primary" />
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
