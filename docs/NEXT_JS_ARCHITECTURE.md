# Next.js Frontend Architecture

**Document Version:** 1.0
**Last Updated:** 2026-01-20
**Status:** Reference Architecture (Not Yet Implemented)

---

## Overview

This document describes the production-grade Next.js frontend architecture for AskChuck, as specified in PRD-07 v2.0. The current implementation uses FastAPI + Streamlit for rapid prototyping. This architecture serves as a reference for future migration to a full production frontend.

**Current Stack:**
- FastAPI server (`src/api/server.py`)
- Streamlit UI (`streamlit_app.py`)

**Target Stack (This Document):**
- Next.js 14 with App Router
- Clerk authentication
- Supabase Postgres
- shadcn/ui components
- Vercel deployment

---

## Why Next.js?

### Advantages Over Streamlit

| Requirement | Streamlit | Next.js |
|-------------|-----------|---------|
| **Professional UI** | Distinctive "prototype" look | Fully customizable branding |
| **Performance** | Full script reruns on interaction | SSR, code splitting, optimized |
| **SEO** | Not search-engine friendly | Pre-rendering, meta tags, OG |
| **Customization** | Limited widget system | Full React component control |
| **TypeScript** | Not supported | Full type safety |
| **Deployment** | Streamlit Cloud (slow) | Vercel (edge, CDN, fast) |

### Production Requirements

1. **Authentication** - Clerk provides user management with generous free tier (10,000 MAU)
2. **Persistence** - Supabase Postgres stores chat sessions with Row Level Security
3. **Streaming** - Server-Sent Events for real-time token display
4. **Responsive Design** - Mobile-first with shadcn/ui components
5. **Observability** - Vercel Analytics and logging

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 14.x (App Router) | SSR, routing, API routes |
| UI Library | React | 18.x | Component architecture |
| UI Components | shadcn/ui | Latest | Accessible Radix UI components |
| Styling | Tailwind CSS | 3.x | Utility-first CSS |
| Authentication | Clerk | Latest | User auth, session management |
| Database | Supabase Postgres | Latest | Chat session persistence |
| State Management | Zustand | 4.x | Lightweight client state |
| HTTP Client | Fetch API | Native | API requests, SSE streaming |
| Markdown | react-markdown | 9.x | Markdown rendering |
| Icons | Lucide React | Latest | Icon library |
| Deployment | Vercel | Free tier | Hosting, edge functions, CDN |

---

## Project Structure

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
│   │
│   ├── sign-in/
│   │   └── [[...sign-in]]/
│   │       └── page.tsx          # Clerk sign-in page
│   │
│   ├── sign-up/
│   │   └── [[...sign-up]]/
│   │       └── page.tsx          # Clerk sign-up page
│   │
│   ├── chat/
│   │   ├── page.tsx              # Main chat interface
│   │   └── layout.tsx            # Chat layout with sidebar
│   │
│   └── api/
│       ├── query/
│       │   └── route.ts          # Streaming SSE endpoint
│       │
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
│   │
│   ├── sidebar/
│   │   ├── Sidebar.tsx           # Sidebar container
│   │   ├── SessionList.tsx       # List of chat sessions
│   │   ├── SessionItem.tsx       # Single session row
│   │   └── UserProfile.tsx       # User info + sign out
│   │
│   └── ui/
│       ├── button.tsx            # shadcn Button
│       ├── card.tsx              # shadcn Card
│       ├── dialog.tsx            # shadcn Dialog (modal)
│       ├── input.tsx             # shadcn Input
│       ├── textarea.tsx          # shadcn Textarea
│       ├── avatar.tsx            # shadcn Avatar
│       ├── badge.tsx             # shadcn Badge
│       ├── separator.tsx         # shadcn Separator
│       └── scroll-area.tsx       # shadcn ScrollArea
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

---

## Database Schema (Supabase Postgres)

### Tables

```sql
-- Chat Sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,           -- Clerk user ID
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    message_count INTEGER NOT NULL DEFAULT 0
);

-- Chat Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    figures JSONB,                   -- Array of figure objects
    sources JSONB,                   -- Array of source objects
    chunk_ids JSONB,                 -- Array of chunk IDs for debugging
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
```

### Row Level Security

```sql
-- Enable RLS
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

---

## API Endpoints

### POST /api/query (Streaming SSE)

Streams RAG response using Server-Sent Events.

**Request:**
```typescript
{
  "question": string,
  "sessionId": string,
  "userId": string  // From Clerk
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
- Calls Python backend `/stream_query` endpoint
- Proxies SSE events to frontend
- Saves complete message to Supabase after streaming completes

### GET /api/sessions

List all chat sessions for the authenticated user.

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

### GET /api/sessions/[id]

Get a specific chat session with all messages.

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

### DELETE /api/sessions/[id]

Delete a chat session and all associated messages.

---

## Authentication (Clerk)

### Setup

1. **Create Clerk Application**
   - Sign up at https://clerk.com
   - Create new application
   - Enable Google OAuth provider
   - Copy API keys

2. **Install Clerk SDK**
   ```bash
   npm install @clerk/nextjs
   ```

3. **Configure Environment Variables**
   ```bash
   # .env.local
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
   NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
   NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/chat
   NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/chat
   ```

4. **Wrap App with ClerkProvider**
   ```typescript
   // app/layout.tsx
   import { ClerkProvider } from '@clerk/nextjs';

   export default function RootLayout({ children }) {
     return (
       <ClerkProvider>
         <html lang="en">
           <body>{children}</body>
         </html>
       </ClerkProvider>
     );
   }
   ```

### Authentication Flow

1. User visits `/chat`
2. Clerk middleware checks authentication
3. If unauthenticated, redirects to `/sign-in`
4. User signs in with Google OAuth
5. Clerk creates session
6. Redirects to `/chat` with authenticated session
7. User ID available via `currentUser()` in server components

---

## Streaming Implementation

### Server-Side (Next.js API Route)

```typescript
// app/api/query/route.ts
import { NextRequest } from 'next/server';
import { currentUser } from '@clerk/nextjs';

export const runtime = 'edge'; // Use edge runtime for streaming

export async function POST(req: NextRequest) {
  const user = await currentUser();
  if (!user) {
    return new Response('Unauthorized', { status: 401 });
  }

  const { question, sessionId } = await req.json();

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Call Python backend streaming endpoint
      const response = await fetch(`${process.env.PYTHON_BACKEND_URL}/stream_query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId, user_id: user.id })
      });

      // Proxy SSE stream to frontend
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            controller.enqueue(encoder.encode(`data: ${line.slice(6)}\n\n`));
          }
        }
      }

      controller.close();
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

### Client-Side (React Component)

```typescript
// components/chat/StreamingMessage.tsx
import { useEffect, useState } from 'react';

export function StreamingMessage({ question, sessionId }) {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);

  useEffect(() => {
    const eventSource = new EventSource('/api/query', {
      method: 'POST',
      body: JSON.stringify({ question, sessionId })
    });

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'token') {
        setContent((prev) => prev + data.content);
      } else if (data.type === 'done') {
        setIsStreaming(false);
        eventSource.close();
      }
    };

    return () => eventSource.close();
  }, [question, sessionId]);

  return (
    <div>
      <ReactMarkdown>{content}</ReactMarkdown>
      {isStreaming && <TypingIndicator />}
    </div>
  );
}
```

---

## shadcn/ui Integration

### Setup

```bash
# Initialize shadcn/ui
npx shadcn-ui@latest init

# Add components
npx shadcn-ui@latest add button card dialog input textarea avatar badge separator scroll-area
```

### Customization for AskChuck Branding

**Color Palette:**
```typescript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#1e40af',      // Blue - academic, trustworthy
        secondary: '#0891b2',    // Cyan - modern, tech
        accent: '#f59e0b',       // Amber - warmth, knowledge
        background: '#ffffff',
        foreground: '#111827',
      }
    }
  }
}
```

**Typography:**
```typescript
// app/layout.tsx
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.className}>
      <body>{children}</body>
    </html>
  );
}
```

---

## Deployment

### Vercel Deployment

1. **Connect GitHub Repository**
   - Go to https://vercel.com
   - Import GitHub repository
   - Vercel auto-detects Next.js

2. **Configure Environment Variables**
   - Add all `.env.local` variables in Vercel dashboard
   - Include Clerk keys, Supabase keys, Python backend URL

3. **Deploy**
   - Automatic deployment on every push to main branch
   - Preview deployments for pull requests

4. **Custom Domain**
   - Configure in Vercel settings
   - Example: `askchuck.com`

### Python Backend Deployment

**Option A: Vercel Serverless Functions**
```json
// vercel.json
{
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.9"
    }
  }
}
```

**Option B: Railway / Render**
- Deploy FastAPI backend separately
- Always-on container (no cold starts)
- Update `PYTHON_BACKEND_URL` in Vercel env vars

---

## Migration Path from Streamlit

### Phase 1: Dual Stack (Current)
- FastAPI server (`src/api/server.py`)
- Streamlit UI (`streamlit_app.py`)
- Both functional and documented

### Phase 2: Next.js Foundation
1. Create Next.js project (`npx create-next-app@latest`)
2. Set up Clerk authentication
3. Set up Supabase Postgres
4. Install shadcn/ui components
5. Configure Tailwind CSS

### Phase 3: Component Migration
1. Build chat interface components
2. Implement streaming message display
3. Add figure display with Cloudflare R2
4. Add source citations
5. Build sidebar with session list

### Phase 4: Backend Integration
1. Connect to existing FastAPI server
2. Implement SSE streaming
3. Save chat sessions to Supabase
4. Test end-to-end flow

### Phase 5: Production Deployment
1. Deploy to Vercel
2. Configure custom domain
3. Set up analytics and monitoring
4. Deprecate Streamlit UI

---

## Environment Variables

### Next.js Frontend

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
# Production: PYTHON_BACKEND_URL=https://askchuck-api.railway.app

# Vercel Analytics (Optional)
NEXT_PUBLIC_VERCEL_ANALYTICS_ID=...
```

---

## Cost Analysis (Free Tiers)

| Service | Free Tier | Limits | Upgrade Cost |
|---------|-----------|--------|--------------|
| Clerk | 10,000 MAU | Monthly active users | $25/month for 10K+ MAU |
| Supabase | 500MB storage | Unlimited API requests | $25/month for 8GB storage |
| Vercel | 100GB bandwidth | Unlimited sites | $20/month for 1TB bandwidth |
| Cloudflare R2 | 10GB storage | Class A: 1M requests/month | $0.015/GB after 10GB |

**Total Free Tier:** Suitable for academic tool with moderate traffic (<1000 users/month)

---

## References

- **PRD-07 v2.0**: `/Users/anuragduddu/code-projects/askchuck/.docs/PRD-07-Frontend.md`
- **Current Implementation Plan**: `/Users/anuragduddu/code-projects/askchuck/docs/plans/2026-01-20-frontend-api.md`
- **Next.js Documentation**: https://nextjs.org/docs
- **Clerk Documentation**: https://clerk.com/docs
- **Supabase Documentation**: https://supabase.com/docs
- **shadcn/ui Documentation**: https://ui.shadcn.com

---

## Conclusion

This Next.js architecture provides a clear path from the current FastAPI + Streamlit prototype to a production-grade frontend with:

- **Professional UI**: Full branding control with shadcn/ui
- **Authentication**: Clerk with generous free tier
- **Persistence**: Supabase Postgres with RLS
- **Streaming**: Real-time token display via SSE
- **Responsive Design**: Mobile-first with Tailwind CSS
- **Deployment**: Vercel with edge functions and CDN

The current Streamlit implementation serves as a functional prototype while this architecture document guides future migration to a scalable, production-ready frontend.
