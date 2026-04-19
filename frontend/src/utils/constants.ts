import type { Stock } from '../types/stock';

export const STOCKS: Stock[] = [
  { ticker: 'AAPL', name: 'Apple Inc.', sector: 'Technology' },
  { ticker: 'MSFT', name: 'Microsoft Corporation', sector: 'Technology' },
  { ticker: 'GOOGL', name: 'Alphabet Inc.', sector: 'Technology' },
  { ticker: 'AMZN', name: 'Amazon.com Inc.', sector: 'Consumer Cyclical' },
  { ticker: 'NVDA', name: 'NVIDIA Corporation', sector: 'Technology' },
  { ticker: 'META', name: 'Meta Platforms Inc.', sector: 'Technology' },
  { ticker: 'TSLA', name: 'Tesla Inc.', sector: 'Consumer Cyclical' },
  { ticker: 'JPM', name: 'JPMorgan Chase & Co.', sector: 'Financial Services' },
  { ticker: 'V', name: 'Visa Inc.', sector: 'Financial Services' },
  { ticker: 'JNJ', name: 'Johnson & Johnson', sector: 'Healthcare' },
  { ticker: 'WMT', name: 'Walmart Inc.', sector: 'Consumer Defensive' },
  { ticker: 'PG', name: 'Procter & Gamble Co.', sector: 'Consumer Defensive' },
  { ticker: 'MA', name: 'Mastercard Inc.', sector: 'Financial Services' },
  { ticker: 'HD', name: 'Home Depot Inc.', sector: 'Consumer Cyclical' },
  { ticker: 'DIS', name: 'Walt Disney Co.', sector: 'Communication Services' },
  { ticker: 'NFLX', name: 'Netflix Inc.', sector: 'Communication Services' },
  { ticker: 'AMD', name: 'Advanced Micro Devices', sector: 'Technology' },
  { ticker: 'PYPL', name: 'PayPal Holdings Inc.', sector: 'Financial Services' },
  { ticker: 'INTC', name: 'Intel Corporation', sector: 'Technology' },
  { ticker: 'CRM', name: 'Salesforce Inc.', sector: 'Technology' },
  { ticker: 'BA', name: 'Boeing Co.', sector: 'Industrials' },
  { ticker: 'NKE', name: 'Nike Inc.', sector: 'Consumer Cyclical' },
  { ticker: 'COIN', name: 'Coinbase Global Inc.', sector: 'Financial Services' },
  { ticker: 'GME', name: 'GameStop Corp.', sector: 'Consumer Cyclical' },
  { ticker: 'AMC', name: 'AMC Entertainment', sector: 'Communication Services' },
  { ticker: 'PLTR', name: 'Palantir Technologies', sector: 'Technology' },
  { ticker: 'SOFI', name: 'SoFi Technologies Inc.', sector: 'Financial Services' },
  { ticker: 'RIVN', name: 'Rivian Automotive Inc.', sector: 'Consumer Cyclical' },
];

export const TIME_RANGES = ['1D', '7D', '1M', '3M'] as const;
export type TimeRange = typeof TIME_RANGES[number];
