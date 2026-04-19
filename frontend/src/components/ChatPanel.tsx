import { useState } from 'react';
import { Send, MessageSquare, Bot, LogIn } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ChatMessage } from '../types/stock';
import { useAuth } from '../contexts/AuthContext';
import { sendChatMessage } from '../services/chatService';
import { useGamification } from '../contexts/GamificationContext';

interface ChatPanelProps {
  ticker: string;
  companyName?: string;
}

export default function ChatPanel({ ticker, companyName }: ChatPanelProps) {
  const { isAuthenticated, getAccessToken } = useAuth();
  const { onSendChatMessage } = useGamification();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSend() {
    const question = input.trim();
    if (!question || isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const token = await getAccessToken();
      if (!token) {
        addBotMessage('Session expired. Please log in again.');
        return;
      }

      const response = await sendChatMessage(ticker, question, companyName || ticker, token);
      addBotMessage(response.answer);
      onSendChatMessage();
    } catch (err: any) {
      addBotMessage(err.message || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  function addBotMessage(content: string) {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: 'assistant',
        content,
        timestamp: new Date(),
      },
    ]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div
      className="overflow-hidden rounded-2xl"
      style={{
        background: 'rgba(26,26,26,0.7)',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 px-5 py-4"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{
            background: 'radial-gradient(circle, rgba(34,197,94,0.2), rgba(34,197,94,0.05))',
            border: '1px solid rgba(34,197,94,0.25)',
          }}
        >
          <MessageSquare className="h-4 w-4 text-brand-400" />
        </div>
        <h2 className="font-semibold text-white">Ask about {ticker}</h2>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{
            background: 'rgba(34,197,94,0.1)',
            border: '1px solid rgba(34,197,94,0.2)',
            color: '#4ade80',
          }}
        >
          AI
        </span>
      </div>

      {/* Messages */}
      <div className="h-80 lg:h-[calc(100vh-220px)] overflow-y-auto p-5">
        {!isAuthenticated ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div
              className="relative mb-4 flex h-14 w-14 items-center justify-center rounded-2xl"
              style={{
                background: 'radial-gradient(circle, rgba(34,197,94,0.15), rgba(34,197,94,0.03))',
                border: '1px solid rgba(34,197,94,0.2)',
              }}
            >
              <LogIn className="h-7 w-7 text-brand-400" />
            </div>
            <h3 className="mb-2 font-semibold text-white">Sign in to chat</h3>
            <p className="mb-4 max-w-xs text-sm text-neutral-500">
              Log in to ask AI-powered questions about {ticker}'s narrative trends and sentiment.
            </p>
            <Link
              to="/login"
              className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white no-underline hover:bg-brand-700"
              style={{ boxShadow: '0 0 12px rgba(34,197,94,0.15)' }}
            >
              Sign in
            </Link>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div
              className="relative mb-4 flex h-14 w-14 items-center justify-center rounded-2xl"
              style={{
                background: 'radial-gradient(circle, rgba(34,197,94,0.15), rgba(34,197,94,0.03))',
                border: '1px solid rgba(34,197,94,0.2)',
              }}
            >
              <Bot className="h-7 w-7 text-brand-400" />
            </div>
            <h3 className="mb-2 font-semibold text-white">MarketNoise AI</h3>
            <p className="max-w-xs text-sm text-neutral-500">
              Ask questions about {ticker}'s narrative trends, sentiment shifts, or hype indicators.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {[
                `Why is ${ticker} trending?`,
                `Sentiment analysis for ${ticker}`,
                `Is ${ticker} overhyped?`,
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="rounded-lg px-3 py-1.5 text-xs text-neutral-400 transition-all hover:text-white"
                  style={{
                    background: 'rgba(36,36,36,0.8)',
                    border: '1px solid rgba(255,255,255,0.07)',
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.borderColor = 'rgba(34,197,94,0.3)';
                    el.style.boxShadow = '0 0 12px rgba(34,197,94,0.1)';
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.borderColor = 'rgba(255,255,255,0.07)';
                    el.style.boxShadow = 'none';
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'user' ? (
                  <div
                    className="max-w-[80%] rounded-2xl rounded-br-sm px-4 py-2.5 text-sm text-white"
                    style={{
                      background: 'linear-gradient(135deg, #16a34a, #15803d)',
                      boxShadow: '0 2px 8px rgba(22,163,74,0.3)',
                    }}
                  >
                    {msg.content}
                  </div>
                ) : (
                  <div
                    className="max-w-[80%] rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-neutral-300"
                    style={{
                      background: 'rgba(36,36,36,0.7)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    {msg.content}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div
                  className="rounded-2xl rounded-bl-sm px-4 py-3"
                  style={{
                    background: 'rgba(36,36,36,0.7)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500" style={{ animationDelay: '0ms' }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500" style={{ animationDelay: '150ms' }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div
          className="flex items-center gap-2 rounded-xl px-4 py-2.5 transition-all focus-within:ring-1 focus-within:ring-brand-600/50"
          style={{
            background: 'rgba(15,15,15,0.8)',
            border: '1px solid rgba(255,255,255,0.08)',
            opacity: isAuthenticated ? 1 : 0.5,
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isAuthenticated ? `Ask about ${ticker}...` : 'Sign in to chat'}
            disabled={!isAuthenticated || isLoading}
            className="flex-1 bg-transparent text-sm text-white placeholder-neutral-500 outline-none disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !isAuthenticated || isLoading}
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white transition-all hover:bg-brand-700 disabled:opacity-30 disabled:cursor-not-allowed"
            style={input.trim() && isAuthenticated ? { boxShadow: '0 0 12px rgba(34,197,94,0.2)' } : {}}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
