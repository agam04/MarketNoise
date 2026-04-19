export interface ChatResponse {
  answer: string;
  ticker: string;
  needs_key?: boolean;
}

export async function sendChatMessage(
  ticker: string,
  question: string,
  companyName: string,
  accessToken: string,
): Promise<ChatResponse> {
  const res = await fetch(`/api/market/chat/${ticker}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ question, company_name: companyName }),
  });

  if (res.status === 401) {
    throw new Error('Please log in to use AI Chat.');
  }
  if (!res.ok) {
    throw new Error('Chat request failed. Please try again.');
  }

  return res.json();
}
