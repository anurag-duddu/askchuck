import { db } from './firebase'
import { collection, addDoc, serverTimestamp } from 'firebase/firestore'

type EventType = 'citation_clicked' | 'pdf_opened' | 'session_started' | 'login' | 'signup' | 'query_completed'

export async function logEvent(
  userId: string | null,
  sessionId: string | null,
  eventType: EventType,
  metadata: Record<string, unknown> = {}
): Promise<void> {
  try {
    await addDoc(collection(db, 'analytics', 'events', 'log'), {
      userId: userId || 'anonymous',
      sessionId: sessionId || '',
      eventType,
      metadata,
      timestamp: serverTimestamp(),
    })
  } catch {
    // Best-effort, never throw
  }
}

export async function logQuery(
  userId: string | null,
  sessionId: string | null,
  question: string,
  latencyMs: number,
  sourcesCount: number,
  figuresCount: number
): Promise<void> {
  try {
    await addDoc(collection(db, 'analytics', 'queries', 'log'), {
      userId: userId || 'anonymous',
      sessionId: sessionId || '',
      questionPreview: question.slice(0, 80),
      latencyMs,
      sourcesCount,
      figuresCount,
      isAnonymous: userId === null,
      timestamp: serverTimestamp(),
    })
  } catch {
    // Best-effort, never throw
  }
}
