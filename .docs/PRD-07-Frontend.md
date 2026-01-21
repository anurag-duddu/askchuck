# PRD-07: Frontend

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-07 |
| Version | v2.0 |
| Phase | 6 |
| Estimated Duration | 4-5 hours |
| Dependencies | PRD-06 (Generation) |
| Owner | Developer |

**Key Changes from v1.0:**
- Switched from **Streamlit** to **Next.js 14 + React** (production-grade framework)
- Switched from Google OAuth to **Clerk** authentication (modern, generous free tier)
- Added **Supabase Postgres** for chat history persistence
- Added **streaming SSE** for real-time token display
- Updated figure URLs from Supabase to **Cloudflare R2**
- Aligned with PRD-06 Llama 3.3 70B and hybrid citation format

---

## Objective

Build a modern, responsive Next.js web application that provides a conversational interface to AskChuck. The frontend must authenticate users via Clerk, persist chat sessions to Supabase Postgres, stream AI responses in real-time using Server-Sent Events, display figures from Cloudflare R2, provide source citations, and offer a clean, professional UX suitable for public academic use.

---

## Background

The frontend is the user's window into AskChuck. While the RAG pipeline (PRD-01 through PRD-06) handles retrieval and generation complexity, the frontend must present this capability in an accessible, professional way.

### Why Next.js Over Streamlit?

The v1.0 PRD proposed Streamlit, but for a public-facing academic tool, Next.js provides critical advantages:

1. **Professional appearance** - Streamlit's distinctive UI looks like a prototype, not a polished tool. Next.js with custom React components delivers a professional, branded experience.

2. **Performance** - Next.js server-side rendering, automatic code splitting, and image optimization provide fast load times. Streamlit reruns the entire script on every interaction.

3. **Customization** - Full control over UI/UX with React components and Tailwind CSS. Streamlit's widget system is rigid and limited.

4. **SEO and sharing** - Next.js enables proper metadata, Open Graph tags, and pre-rendering for link previews. Streamlit apps are black boxes to search engines.

5. **Deployment flexibility** - Vercel free tier, edge functions, global CDN. Streamlit Cloud is limited and slower.

6. **TypeScript support** - Type safety throughout the stack, catching errors at build time.

7. **shadcn/ui components** - Accessible, customizable React components built on Radix UI. Unlike rigid component libraries, shadcn/ui components are copied into your project and can be fully customized for AskChuck branding. This enables a professional, polished UI with consistent design language while maintaining full control over styling and behavior.

### Key Design Principles

1. **Streaming responses** - Use Server-Sent Events (SSE) to stream tokens from Groq Llama 3.3 70B, providing real-time feedback. Users see progress immediately, making the system feel fast and responsive.

2. **Persistent conversations** - Store chat sessions in Supabase Postgres with user association. Users can return days later and resume conversations.

3. **Figure-rich responses** - Display Cloudflare R2 figures prominently with captions. Owen's visual concepts (Information Structures, Abstraction Ladders) are central to understanding.

4. **Source transparency** - Show [Document, Section] citations inline and in expandable drawers. Users trust responses grounded in sources.

5. **Mobile-first responsive** - Works seamlessly on desktop, tablet, and mobile. Touch-friendly controls, readable text, clean layout.

---

## Functional Requirements

### FR-01: User Authentication (Clerk)

The system shall authenticate users via Clerk before granting access.

**Acceptance Criteria:**
- Sign-in page with Clerk pre-built components
- Support for Google OAuth, email/password, and passkeys
- Redirects to chat after successful authentication
- Displays user name and avatar when authenticated
- Sign-out functionality
- Session persistence across page refreshes
- Free tier: 10,000 monthly active users

### FR-02: Chat Interface

The system shall provide a modern conversational chat interface.

**Acceptance Criteria:**
- Clean, centered chat layout with message bubbles
- Text input field with send button and Enter key support
- User messages right-aligned with distinct styling
- Assistant messages left-aligned with AskChuck avatar
- Automatic scrolling to newest messages
- Loading indicator during retrieval phase
- Smooth animations for message appearance

### FR-03: Streaming Response Display

The system shall stream AI responses in real-time using Server-Sent Events.

**Acceptance Criteria:**
- Tokens appear character-by-character as generated
- No full-response wait time
- Smooth streaming without visual jitter
- Loading state during retrieval (before streaming starts)
- Streaming indicator (typing animation) during token generation
- Fallback to standard response if SSE fails
- Stream terminates cleanly on completion

### FR-04: Response Formatting

The system shall display AI responses with rich formatting.

**Acceptance Criteria:**
- Markdown rendering with proper styles
- Code block syntax highlighting (if present)
- Inline citations in [Document, Section] format highlighted
- Owen terminology with subtle visual distinction
- Line breaks and paragraphs preserved
- Links clickable (if present)

### FR-05: Figure Display (Cloudflare R2)

The system shall display relevant figures inline with responses.

**Acceptance Criteria:**
- Images loaded from Cloudflare R2 URLs (r2_url field)
- Figures displayed with captions below image
- Maximum 3 figures per response (as per PRD-06)
- Click to enlarge/zoom modal
- Lazy loading for performance
- Graceful handling of missing/failed images
- Figure source attribution (document title)

### FR-06: Source Citations

The system shall display source citations for each response.

**Acceptance Criteria:**
- Expandable/collapsible source drawer at bottom of response
- [Document Title, Section] format for each source
- Multiple sources deduplicated
- Visual distinction from response text
- Chunk IDs stored but not displayed to user (available in console for debugging)

### FR-07: Chat Session Persistence (Supabase)

The system shall persist chat sessions to Supabase Postgres.

**Acceptance Criteria:**
- Each chat session stored with unique ID
- Messages saved with role, content, figures, sources, timestamp
- Sessions associated with authenticated user (Clerk user ID)
- Sessions automatically saved after each message pair
- Session list displays in sidebar with titles
- Session title auto-generated from first user message
- Load previous sessions on click
- Delete session functionality

### FR-08: Sidebar Navigation

The system shall provide a sidebar for session management.

**Acceptance Criteria:**
- "New Chat" button to start fresh conversation
- Session history list (most recent first)
- Current session highlighted
- Session titles truncated if too long
- Scroll for long session lists
- Collapsible on mobile
- User profile section with sign-out button

### FR-09: Responsive Design

The system shall work seamlessly across all screen sizes.

**Acceptance Criteria:**
- Desktop: sidebar + chat area (two-column layout)
- Tablet: collapsible sidebar, full-width chat
- Mobile: hamburger menu sidebar, full-width chat
- Touch-friendly controls (44px minimum touch targets)
- Readable text at all sizes
- Figure images scale appropriately
- Input field always accessible (sticky bottom)

### FR-10: Error Handling

The system shall handle errors gracefully.

**Acceptance Criteria:**
- API failures display user-friendly error messages
- Retry mechanism for transient failures
- Fallback to standard query if streaming fails
- Network offline indicator
- Session save failures logged and retried
- Image load failures show placeholder

---

## Technical Specification

### Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | Next.js | 14.x (App Router) | Server-side rendering, API routes, streaming |
| UI Library | React | 18.x | Component architecture |
| UI Components | shadcn/ui | Latest | Accessible, customizable components built on Radix UI |
| Styling | Tailwind CSS | 3.x | Utility-first styling, responsive design |
| Authentication | Clerk | Latest | User authentication, session management |
| Database | Supabase Postgres | Latest | Chat session persistence |
| State Management | Zustand | 4.x | Client-side state (lighter than Redux) |
| HTTP Client | Fetch API | Native | API requests, SSE streaming |
| Markdown | react-markdown | 9.x | Markdown rendering |
| Icons | Lucide React | Latest | Icon library |
| Deployment | Vercel | Free tier | Hosting, edge functions, CDN |

### Project Structure

```
askchuck-frontend/
├── .env.local                    # Environment variables
├── next.config.js                # Next.js configuration
├── tailwind.config.js            # Tailwind configuration
├── tsconfig.json                 # TypeScript configuration
│
├── app/
│   ├── layout.tsx                # Root layout (Clerk provider)
│   ├── page.tsx                  # Landing page (redirects to /chat)
│   ├── sign-in/
│   │   └── [[...sign-in]]/
│   │       └── page.tsx          # Clerk sign-in page
│   ├── sign-up/
│   │   └── [[...sign-up]]/
│   │       └── page.tsx          # Clerk sign-up page
│   ├── chat/
│   │   ├── page.tsx              # Main chat interface
│   │   └── layout.tsx            # Chat layout with sidebar
│   └── api/
│       ├── query/
│       │   └── route.ts          # Streaming SSE endpoint
│       └── sessions/
│           ├── route.ts          # List/create sessions
│           └── [id]/
│               └── route.ts      # Get/update/delete session
│
├── components/
│   ├── chat/
│   │   ├── ChatContainer.tsx     # Main chat UI
│   │   ├── MessageList.tsx       # Scrollable message list
│   │   ├── Message.tsx           # Single message component
│   │   ├── ChatInput.tsx         # Input field + send button
│   │   ├── StreamingMessage.tsx  # Message with streaming state
│   │   ├── FigureDisplay.tsx     # Figure grid/carousel
│   │   ├── SourceCitations.tsx   # Expandable source drawer
│   │   └── TypingIndicator.tsx   # Loading animation
│   ├── sidebar/
│   │   ├── Sidebar.tsx           # Sidebar container
│   │   ├── SessionList.tsx       # List of chat sessions
│   │   ├── SessionItem.tsx       # Single session row
│   │   └── UserProfile.tsx       # User info + sign out
│   └── ui/
│       ├── Button.tsx            # Reusable button
│       ├── Modal.tsx             # Image zoom modal
│       └── Spinner.tsx           # Loading spinner
│
├── lib/
│   ├── supabase.ts               # Supabase client
│   ├── askchuck-api.ts           # Python backend API client
│   └── stores/
│       └── chatStore.ts          # Zustand chat state
│
├── types/
│   ├── chat.ts                   # Chat message types
│   └── api.ts                    # API response types
│
└── public/
    ├── askchuck-logo.svg         # AskChuck branding
    └── placeholder-figure.svg    # Fallback for failed images
```

### Database Schema (Supabase Postgres)

```sql
-- Enable Row Level Security
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL, -- Clerk user ID
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    message_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    figures JSONB, -- Array of figure objects
    sources JSONB, -- Array of source objects
    chunk_ids JSONB, -- Array of chunk IDs for debugging
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);

-- Row Level Security policies
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own sessions
CREATE POLICY "Users can access own sessions"
ON chat_sessions FOR ALL
USING (user_id = current_setting('app.current_user_id', true));

-- Policy: Users can only access messages from their own sessions
CREATE POLICY "Users can access own messages"
ON chat_messages FOR ALL
USING (
    session_id IN (
        SELECT id FROM chat_sessions
        WHERE user_id = current_setting('app.current_user_id', true)
    )
);
```

### API Endpoints

#### POST /api/query (Streaming SSE)

**Request:**
```typescript
{
  "question": string,
  "sessionId": string,
  "userId": string // From Clerk
}
```

**Response (Server-Sent Events):**
```
event: token
data: {"content": "A"}

event: token
data: {"content": " Design"}

event: figures
data: {"figures": [...]}

event: sources
data: {"sources": [...]}

event: done
data: {}
```

**Implementation:**
- Calls Python backend `src/generation/rag_chain.py` stream_query()
- Proxies SSE events to frontend
- Saves complete message to Supabase after streaming completes

#### GET /api/sessions

**Response:**
```typescript
{
  "sessions": [
    {
      "id": string,
      "title": string,
      "createdAt": string,
      "updatedAt": string,
      "messageCount": number
    }
  ]
}
```

#### GET /api/sessions/[id]

**Response:**
```typescript
{
  "session": {
    "id": string,
    "title": string,
    "messages": [
      {
        "id": string,
        "role": "user" | "assistant",
        "content": string,
        "figures": [...],
        "sources": [...],
        "createdAt": string
      }
    ]
  }
}
```

#### DELETE /api/sessions/[id]

Deletes a chat session and all associated messages.

---

## Implementation Details

### File: app/api/query/route.ts

```typescript
/**
 * Streaming SSE endpoint for AskChuck queries.
 * Proxies stream_query() from Python backend and saves to Supabase.
 */

import { NextRequest } from 'next/server';
import { currentUser } from '@clerk/nextjs';
import { createClient } from '@/lib/supabase';

export const runtime = 'edge'; // Use edge runtime for streaming

export async function POST(req: NextRequest) {
  // Verify authentication
  const user = await currentUser();
  if (!user) {
    return new Response('Unauthorized', { status: 401 });
  }

  const { question, sessionId } = await req.json();

  // Create SSE stream
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Call Python backend streaming endpoint
        const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/stream_query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question,
            session_id: sessionId,
            user_id: user.id
          })
        });

        if (!response.body) {
          throw new Error('No response body');
        }

        // Proxy the Python SSE stream to frontend
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullAnswer = '';
        let figures: any[] = [];
        let sources: any[] = [];
        let chunkIds: string[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6));

              // Forward to frontend
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify(data)}\n\n`)
              );

              // Accumulate for Supabase save
              if (data.type === 'token') {
                fullAnswer += data.content;
              } else if (data.type === 'figures') {
                figures = data.figures;
              } else if (data.type === 'sources') {
                sources = data.sources;
              } else if (data.type === 'chunk_ids') {
                chunkIds = data.chunk_ids;
              }
            }
          }
        }

        // Save to Supabase after streaming completes
        const supabase = createClient();

        // Save user message
        await supabase.from('chat_messages').insert({
          session_id: sessionId,
          role: 'user',
          content: question
        });

        // Save assistant message
        await supabase.from('chat_messages').insert({
          session_id: sessionId,
          role: 'assistant',
          content: fullAnswer,
          figures,
          sources,
          chunk_ids: chunkIds
        });

        // Update session updated_at and message_count
        await supabase.rpc('increment_message_count', { session_id: sessionId });

        // Signal stream completion
        controller.enqueue(encoder.encode('data: {"type": "done"}\n\n'));
        controller.close();

      } catch (error) {
        console.error('Streaming error:', error);
        controller.error(error);
      }
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    }
  });
}
```

### File: components/chat/StreamingMessage.tsx

```typescript
/**
 * Message component with real-time streaming display.
 */

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FigureDisplay } from './FigureDisplay';
import { SourceCitations } from './SourceCitations';
import { TypingIndicator } from './TypingIndicator';

interface StreamingMessageProps {
  question: string;
  sessionId: string;
  onComplete: (message: AssistantMessage) => void;
}

export function StreamingMessage({ question, sessionId, onComplete }: StreamingMessageProps) {
  const [streamedContent, setStreamedContent] = useState('');
  const [figures, setFigures] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [isStreaming, setIsStreaming] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const eventSource = new EventSource('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, sessionId })
    });

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'token') {
        setStreamedContent((prev) => prev + data.content);
      } else if (data.type === 'figures') {
        setFigures(data.figures);
      } else if (data.type === 'sources') {
        setSources(data.sources);
      } else if (data.type === 'done') {
        setIsStreaming(false);
        eventSource.close();
        onComplete({
          role: 'assistant',
          content: streamedContent,
          figures,
          sources
        });
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      setError('Failed to stream response. Please try again.');
      setIsStreaming(false);
      eventSource.close();
    };

    return () => eventSource.close();
  }, [question, sessionId]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-semibold">
          📚
        </div>
        <div className="flex-1">
          <ReactMarkdown className="prose prose-sm max-w-none">
            {streamedContent}
          </ReactMarkdown>

          {isStreaming && <TypingIndicator />}

          {figures.length > 0 && <FigureDisplay figures={figures} />}

          {sources.length > 0 && <SourceCitations sources={sources} />}
        </div>
      </div>
    </div>
  );
}
```

### File: lib/supabase.ts

```typescript
/**
 * Supabase client for chat session persistence.
 */

import { createClient as createSupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export function createClient() {
  return createSupabaseClient(supabaseUrl, supabaseAnonKey);
}

export async function createChatSession(userId: string, title: string) {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('chat_sessions')
    .insert({ user_id: userId, title })
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function getChatSessions(userId: string) {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('chat_sessions')
    .select('id, title, created_at, updated_at, message_count')
    .eq('user_id', userId)
    .order('updated_at', { ascending: false });

  if (error) throw error;
  return data;
}

export async function getChatMessages(sessionId: string) {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('chat_messages')
    .select('*')
    .eq('session_id', sessionId)
    .order('created_at', { ascending: true });

  if (error) throw error;
  return data;
}

export async function deleteChatSession(sessionId: string) {
  const supabase = createClient();
  const { error } = await supabase
    .from('chat_sessions')
    .delete()
    .eq('id', sessionId);

  if (error) throw error;
}
```

### File: app/layout.tsx

```typescript
/**
 * Root layout with Clerk authentication provider.
 */

import { ClerkProvider } from '@clerk/nextjs';
import './globals.css';

export const metadata = {
  title: 'AskChuck - Owen\'s Structured Planning',
  description: 'Explore Charles Owen\'s Structured Planning methodology through AI-powered conversation',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

### File: .env.local

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/chat
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/chat

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Python Backend API
PYTHON_BACKEND_URL=http://localhost:8000
# For production: PYTHON_BACKEND_URL=https://askchuck-api.vercel.app

# Optional: Analytics
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=...
```

---

## Python Backend API Additions

The Next.js frontend requires a Python FastAPI backend to expose the RAG chain via HTTP/SSE.

### File: backend/main.py

```python
"""
FastAPI backend for AskChuck.
Exposes RAG chain for Next.js frontend consumption.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from src.generation.rag_chain import get_rag_chain

app = FastAPI(title="AskChuck API")

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://askchuck.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    session_id: str
    user_id: str

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/stream_query")
async def stream_query(request: QueryRequest):
    """Stream RAG response via SSE."""
    rag_chain = get_rag_chain()

    async def generate():
        try:
            for event in rag_chain.stream_query(
                question=request.question,
                conversation_history=[]  # Loaded from Supabase in Next.js
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/query")
async def query(request: QueryRequest):
    """Standard (non-streaming) query endpoint."""
    rag_chain = get_rag_chain()

    try:
        response = rag_chain.query(
            question=request.question,
            conversation_history=[]
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## shadcn/ui Setup

shadcn/ui is a collection of re-usable components built on Radix UI and Tailwind CSS. Unlike traditional component libraries, shadcn/ui components are copied directly into your project, giving you full ownership and customization control.

### Installation

```bash
# Initialize shadcn/ui in your Next.js project
npx shadcn-ui@latest init

# Add components as needed
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add input
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add avatar
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add scroll-area
```

### shadcn MCP Server

Install the shadcn MCP server for Claude Code to have native access to component documentation and usage patterns:

```bash
# Install shadcn MCP server
npm install -g @modelcontextprotocol/server-shadcn

# Add to Claude Code MCP servers configuration
# This enables Claude to reference shadcn components and provide accurate usage examples
```

### AskChuck Branding

All shadcn/ui components will be customized with AskChuck branding:

**Color Palette:**
- Primary: `#1e40af` (Blue - academic, trustworthy)
- Secondary: `#0891b2` (Cyan - modern, tech)
- Accent: `#f59e0b` (Amber - warmth, knowledge)
- Background: `#ffffff` / `#f9fafb` (Clean, readable)
- Text: `#111827` / `#6b7280` (High contrast)

**Typography:**
- Headings: Inter (clean, modern sans-serif)
- Body: Inter (consistent, readable)
- Monospace: JetBrains Mono (for code blocks, chunk IDs)

**Component Customization:**
- Button: Rounded corners, subtle shadows, hover states
- Card: Soft borders, minimal shadows for message bubbles
- Dialog: Smooth animations for figure zoom modal
- Input: Clear focus states, proper accessibility labels

**Brand Identity:**
- Logo: 📚 emoji or custom SVG with "AskChuck" wordmark
- Tagline: "Explore Owen's Structured Planning"
- Tone: Professional, educational, approachable

---

## Configuration Parameters

| Parameter | Default Value | Purpose | Notes |
|-----------|--------------|---------|-------|
| `CLERK_FREE_TIER` | 10,000 MAU | Monthly active users | Generous for academic tool |
| `SUPABASE_FREE_TIER` | 500MB storage | Chat session persistence | Unlimited API requests |
| `VERCEL_FREE_TIER` | 100GB bandwidth | Hosting + edge functions | Sufficient for moderate traffic |
| `STREAMING_ENABLED` | Always on | Real-time token display | Per user decision (Q4) |
| `MAX_FIGURES_DISPLAY` | 3 | Figures per response | Aligned with PRD-06 |
| `SESSION_TITLE_LENGTH` | 50 characters | Auto-generated from first message | Truncated with "..." |
| `MESSAGE_RETENTION` | Unlimited | No automatic deletion | User can manually delete sessions |

---

## Deployment

### Vercel Deployment (Frontend)

1. **Connect GitHub repository** to Vercel
2. **Set environment variables** in Vercel dashboard
3. **Deploy** - Automatic on every push to main branch
4. **Custom domain** - Configure in Vercel settings

### Python Backend Deployment

**Option A: Vercel Serverless Functions**
- Deploy Python FastAPI as Vercel serverless function
- Requires `vercel.json` configuration
- Cold start latency (~1-2s)

**Option B: Railway / Render**
- Deploy Python backend separately
- Always-on container (no cold starts)
- Free tier: Railway (512MB RAM), Render (512MB RAM)

**Option C: Modal Labs**
- Serverless GPU inference if needed (not required for current stack)

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| ✅ Clerk authentication works | Sign in with Google, verify session |
| ✅ Chat messages display correctly | Send message, verify rendering |
| ✅ Streaming responses work | Verify tokens appear in real-time |
| ✅ Figures display from Cloudflare R2 | Query visual concept, verify image loads |
| ✅ Sources are expandable | Click sources drawer |
| ✅ Sessions persist to Supabase | Reload page, verify messages present |
| ✅ New chat creates new session | Click new chat, verify empty state |
| ✅ Session history loads | Click previous session, verify messages load |
| ✅ Sign out works | Click sign out, verify redirect to login |
| ✅ Responsive on mobile | Test at 375px width |
| ✅ Styling is professional | Visual review |
| ✅ SSE fallback works | Test with SSE disabled |
| ✅ Error handling graceful | Disconnect network, verify error message |

---

## Testing Checklist

### Authentication
- [ ] Sign up with Google OAuth
- [ ] Sign in with email/password
- [ ] Sign out and verify redirect
- [ ] Session persistence across refreshes

### Chat Functionality
- [ ] Send message and receive streaming response
- [ ] Multiple messages in conversation
- [ ] Follow-up questions with context
- [ ] Markdown rendering (bold, italics, lists)
- [ ] Citations display correctly

### Figures
- [ ] Query "What is an Information Structure?" - verify figure displays
- [ ] Click to enlarge figure
- [ ] Multiple figures in grid layout
- [ ] Figure caption and attribution

### Session Management
- [ ] New chat creates new session
- [ ] Session saved to Supabase
- [ ] Load previous session from sidebar
- [ ] Delete session
- [ ] Session title auto-generated

### Performance
- [ ] First paint < 2s
- [ ] Streaming starts < 1s after retrieval completes
- [ ] No layout shift during streaming
- [ ] Smooth scrolling

### Mobile
- [ ] Responsive layout on iPhone SE (375px)
- [ ] Touch-friendly controls
- [ ] Sidebar collapses to hamburger menu
- [ ] Input field always accessible

---

## Next Steps

Once the frontend is functional and deployed, proceed to **PRD-08: Evaluation** to build the testing and evaluation framework.
