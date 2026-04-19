# Frontend — React + TypeScript + Vite + Tailwind CSS

The MarketNoise frontend is an interactive dashboard that lets users search stocks, view live prices and charts, explore narrative analysis, chat with an AI assistant, and browse trending news.

## Quick Start

```bash
cd frontend
npm install
npm run dev         # http://localhost:5173
npm run build       # Production build
npm run preview     # Preview production build
```

## Environment Variables

Create a `.env` file in this directory:

```
VITE_GNEWS_API_KEY=your_gnews_api_key_here
```

- **GNews API key** — Get a free key at [gnews.io](https://gnews.io) (100 requests/day). Required for the news section.
- **Stock prices** — Work out of the box via Yahoo Finance (no key needed). Uses a Vite dev proxy to avoid CORS.

## Pages

| Route | Page | Description |
|---|---|---|
| `/` | **HomePage** | Landing page with autocomplete stock search + feature cards |
| `/stock/:ticker` | **StockPage** | Full stock detail — price, chart, analysis, chat, news |

## Project Structure

```
src/
├── components/
│   ├── Navbar.tsx              # Top navigation bar with logo + links
│   ├── SearchBar.tsx           # Autocomplete stock search (28 tickers)
│   ├── PriceChart.tsx          # Interactive price chart (1D/7D/1M/3M) using Recharts
│   ├── AnalysisSection.tsx     # Sentiment, velocity, hype risk cards
│   ├── ChatPanel.tsx           # LLM chat interface (UI only for now)
│   └── NewsSection.tsx         # Trending news articles from GNews
│
├── pages/
│   ├── HomePage.tsx            # Search + feature highlights
│   └── StockPage.tsx           # Stock detail view (assembles all components)
│
├── services/
│   ├── stockService.ts         # Yahoo Finance API — quotes + price history
│   └── newsService.ts          # GNews API — stock news articles
│
├── types/
│   └── stock.ts                # TypeScript interfaces (Stock, PricePoint, NewsItem, ChatMessage)
│
├── utils/
│   └── constants.ts            # Stock ticker list, time range definitions
│
├── App.tsx                     # Router setup (BrowserRouter + Routes)
├── main.tsx                    # Entry point
└── index.css                   # Tailwind imports + custom theme (dark mode, brand colors)
```

## Data Flow

### Stock Prices (Yahoo Finance)
- **No API key required**
- Vite dev proxy: `/api/yahoo/*` → `query1.finance.yahoo.com`
- `fetchQuote(ticker)` — live price, daily change, % change
- `fetchPriceHistory(ticker, range)` — historical price points for chart
- Built-in **5-minute cache** and **retry with backoff** to handle Yahoo's rate limits (429 errors)

### News (GNews API)
- Requires `VITE_GNEWS_API_KEY` in `.env`
- `fetchStockNews(ticker, companyName)` — up to 6 recent articles
- Graceful fallback when key is missing (shows instruction message)

## Design System

- **Theme**: Dark mode (bg `#0f0f0f`, cards `#1a1a1a`)
- **Brand colors**: Green palette (`#052e16` → `#86efac`)
- **Accent colors**: Red for negative (`#ef4444`), Yellow for warnings (`#f59e0b`)
- **Icons**: Lucide React
- **Charts**: Recharts (AreaChart with green gradient)
- **Responsive**: Mobile-friendly layout

## Key Dependencies

| Package | Purpose |
|---|---|
| `react-router-dom` | Client-side routing |
| `recharts` | Price charts |
| `lucide-react` | Icons |
| `tailwindcss` | Styling |

## Adding a New Component

1. Create the component in `src/components/`
2. If it needs API data, add a service function in `src/services/`
3. Add TypeScript types in `src/types/stock.ts`
4. Wire it into the relevant page (`HomePage.tsx` or `StockPage.tsx`)
