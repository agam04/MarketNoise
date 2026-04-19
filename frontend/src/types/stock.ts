export interface Stock {
  ticker: string;
  name: string;
  sector: string;
}

export interface PricePoint {
  date: string;
  price: number;
}

export interface SentimentData {
  positive: number;
  negative: number;
  neutral: number;
  overall: 'positive' | 'negative' | 'neutral' | 'mixed';
}

export interface VelocityData {
  score: number;
  trend: 'accelerating' | 'decelerating' | 'stable';
  changePercent: number;
}

export interface HypeData {
  score: number;
  level: 'low' | 'moderate' | 'high' | 'extreme';
}

export interface NewsItem {
  id: string;
  headline: string;
  source: string;
  timestamp: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  url: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}
