// frontend/src/components/ChatComponent.tsx (Corrected)

import React, { useState, useEffect, useRef } from 'react';
import { sendMessage } from '../api/api'; // Assuming sendMessage is updated in api.ts
import { HistoryPart } from '../api/api';

// Define the type for a single message in the chat history
interface Message {
  role: 'user' | 'ai';
  text: string;
}

const ChatComponent: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', text: input };
    
    // History to be sent to the API (includes previous messages only)
    const historyPayload = messages.map(msg => ({ 
        role: msg.role === 'ai' ? 'model' : 'user', 
        text: msg.text 
    })) as HistoryPart[]; 
    
    // 1. Update the local state with the user's message immediately
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // 2. Call the secured /api/core/chat endpoint, 
      //    passing the current user's message AND the history payload.
      const response = await sendMessage(userMessage.text, historyPayload);
      const aiResponse = response.data.response;
      
      // 3. Add AI response to history
      setMessages(prev => [...prev, { role: 'ai', text: aiResponse }]);

    } catch (error) {
      console.error("AI Chat Error:", error);
      setMessages(prev => [...prev, { role: 'ai', text: 'Sorry, I ran into an error connecting to the AI service.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ margin: '20px auto', maxWidth: '600px', border: '1px solid #ccc', borderRadius: '8px', display: 'flex', flexDirection: 'column', height: '60vh' }}>
      
      {/* --- Chat History Display --- */}
      <div style={{ flexGrow: 1, padding: '10px', overflowY: 'auto', background: '#f9f9f9' }}>
        {messages.map((msg, index) => (
          <div 
            key={index} 
            style={{ 
              marginBottom: '10px', 
              textAlign: msg.role === 'user' ? 'right' : 'left' 
            }}
          >
            <span 
              style={{
                display: 'inline-block',
                padding: '8px 12px',
                borderRadius: '15px',
                background: msg.role === 'user' ? '#007bff' : '#e0e0e0',
                color: msg.role === 'user' ? 'white' : 'black',
                whiteSpace: 'pre-wrap' // Important for handling tool output formatting
              }}
            >
              {msg.text}
            </span>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {/* --- Input Form --- */}
      <form onSubmit={handleSend} style={{ display: 'flex', padding: '10px', borderTop: '1px solid #ccc' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isLoading ? "AI is thinking..." : "Ask me anything (Report, Search, Claim)..."}
          disabled={isLoading}
          style={{ flexGrow: 1, padding: '10px', border: '1px solid #ddd', borderRadius: '4px 0 0 4px' }}
        />
        <button 
          type="submit" 
          disabled={!input.trim() || isLoading}
          style={{ padding: '10px 15px', background: '#28a745', color: 'white', border: 'none', borderRadius: '0 4px 4px 0', cursor: 'pointer' }}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default ChatComponent;