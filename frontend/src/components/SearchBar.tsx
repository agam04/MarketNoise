import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, TrendingUp, Loader2 } from 'lucide-react';
import { searchStocks } from '../services/searchService';
import type { Stock } from '../types/stock';
import { useGamification } from '../contexts/GamificationContext';

interface SearchBarProps {
  large?: boolean;
}

export default function SearchBar({ large = false }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Stock[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { onSearchStock } = useGamification();

  // Debounced search via Twelve Data API
  useEffect(() => {
    if (query.trim().length === 0) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    setIsSearching(true);
    const timer = setTimeout(() => {
      searchStocks(query)
        .then((stocks) => {
          setResults(stocks);
          setIsOpen(stocks.length > 0);
          setActiveIndex(-1);
        })
        .finally(() => setIsSearching(false));
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function selectStock(ticker: string) {
    setQuery('');
    setIsOpen(false);
    onSearchStock();
    navigate(`/stock/${ticker}`);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!isOpen) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      selectStock(results[activeIndex].ticker);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  }

  return (
    <div className="relative w-full">
      <div
        className={`flex items-center gap-3 rounded-xl border border-surface-600 bg-surface-800 transition-all focus-within:border-brand-600 focus-within:ring-1 focus-within:ring-brand-600/50 ${
          large ? 'px-5 py-4' : 'px-4 py-2.5'
        }`}
      >
        {isSearching ? (
          <Loader2 className={`animate-spin text-brand-500 ${large ? 'h-6 w-6' : 'h-5 w-5'}`} />
        ) : (
          <Search className={`text-neutral-500 ${large ? 'h-6 w-6' : 'h-5 w-5'}`} />
        )}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="Search any US stock — e.g. AAPL, Tesla, NVIDIA..."
          className={`w-full bg-transparent text-white placeholder-neutral-500 outline-none ${
            large ? 'text-lg' : 'text-sm'
          }`}
        />
      </div>

      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 z-50 mt-2 w-full overflow-hidden rounded-xl border border-surface-600 bg-surface-800 shadow-2xl"
        >
          {results.map((stock, i) => (
            <button
              key={stock.ticker}
              onClick={() => selectStock(stock.ticker)}
              className={`flex w-full items-center gap-3 px-5 py-3 text-left transition-colors ${
                i === activeIndex
                  ? 'bg-brand-900/40 text-white'
                  : 'text-neutral-300 hover:bg-surface-700'
              }`}
            >
              <TrendingUp className="h-4 w-4 shrink-0 text-brand-500" />
              <div className="flex flex-1 items-center justify-between min-w-0">
                <div className="min-w-0">
                  <span className="font-semibold text-white">{stock.ticker}</span>
                  <span className="ml-2 text-sm text-neutral-400 truncate">{stock.name}</span>
                </div>
                <span className="ml-2 shrink-0 text-xs text-neutral-500">{stock.sector}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
