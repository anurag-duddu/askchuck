"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import {
  collection,
  doc,
  addDoc,
  updateDoc,
  deleteDoc,
  getDocs,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  serverTimestamp,
  increment,
  Timestamp,
} from "firebase/firestore";
import { db } from "@/lib/firebase";
import { useAuth } from "@/contexts/AuthContext";
import { ChatMessage } from "@/types/chat";

export interface Session {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
}

interface SessionContextValue {
  currentSessionId: string | null;
  sessions: Session[];
  createSession: (firstQuestion: string) => Promise<string>;
  saveMessage: (sessionId: string, message: ChatMessage) => Promise<void>;
  loadSessionMessages: (sessionId: string) => Promise<ChatMessage[]>;
  deleteSession: (sessionId: string) => Promise<void>;
}

export const SessionContext = createContext<SessionContextValue>({
  currentSessionId: null,
  sessions: [],
  createSession: async () => "",
  saveMessage: async () => {},
  loadSessionMessages: async () => [],
  deleteSession: async () => {},
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Subscribe to the user's sessions in real time (limit 20, ordered by updatedAt desc)
  useEffect(() => {
    if (!user) {
      setSessions([]);
      setCurrentSessionId(null);
      return;
    }

    const q = query(
      collection(db, "sessions"),
      where("userId", "==", user.uid),
      orderBy("updatedAt", "desc"),
      limit(20)
    );

    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const loaded: Session[] = snapshot.docs.map((docSnap) => {
          const data = docSnap.data();
          const toDate = (v: unknown): Date => {
            if (v instanceof Timestamp) return v.toDate();
            if (v instanceof Date) return v;
            return new Date();
          };
          return {
            id: docSnap.id,
            title: data.title ?? "",
            createdAt: toDate(data.createdAt),
            updatedAt: toDate(data.updatedAt),
            messageCount: data.messageCount ?? 0,
          };
        });
        setSessions(loaded);
      },
      (err) => {
        console.error("SessionContext: onSnapshot error", err);
      }
    );

    return unsubscribe;
  }, [user]);

  const createSession = useCallback(
    async (firstQuestion: string): Promise<string> => {
      if (!user) return "";
      const docRef = await addDoc(collection(db, "sessions"), {
        userId: user.uid,
        title: firstQuestion.slice(0, 60),
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
        messageCount: 0,
      });
      setCurrentSessionId(docRef.id);
      return docRef.id;
    },
    [user]
  );

  const saveMessage = useCallback(
    async (sessionId: string, message: ChatMessage): Promise<void> => {
      if (!user || !sessionId) return;
      const messagesRef = collection(db, "sessions", sessionId, "messages");
      await addDoc(messagesRef, {
        role: message.role,
        content: message.content,
        sources: message.sources ?? [],
        figures: message.figures ?? [],
        createdAt: serverTimestamp(),
      });
      // Update parent session metadata
      const sessionRef = doc(db, "sessions", sessionId);
      await updateDoc(sessionRef, {
        updatedAt: serverTimestamp(),
        messageCount: increment(1),
      });
    },
    [user]
  );

  const loadSessionMessages = useCallback(
    async (sessionId: string): Promise<ChatMessage[]> => {
      if (!user || !sessionId) return [];
      const messagesRef = collection(db, "sessions", sessionId, "messages");
      const q = query(messagesRef, orderBy("createdAt", "asc"));
      const snapshot = await getDocs(q);
      return snapshot.docs.map((docSnap, idx) => {
        const data = docSnap.data();
        const toIso = (v: unknown): string => {
          if (v instanceof Timestamp) return v.toDate().toISOString();
          if (v instanceof Date) return v.toISOString();
          return new Date().toISOString();
        };
        return {
          id: docSnap.id,
          role: data.role as "user" | "assistant",
          content: data.content ?? "",
          sources: data.sources ?? [],
          figures: data.figures ?? [],
          created_at: toIso(data.createdAt),
          isStreaming: false,
          // Ensure unique id fallback
        } satisfies ChatMessage;
        void idx;
      });
    },
    [user]
  );

  const deleteSession = useCallback(
    async (sessionId: string): Promise<void> => {
      if (!user || !sessionId) return;
      await deleteDoc(doc(db, "sessions", sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
    },
    [user, currentSessionId]
  );

  return (
    <SessionContext.Provider
      value={{
        currentSessionId,
        sessions,
        createSession,
        saveMessage,
        loadSessionMessages,
        deleteSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  return useContext(SessionContext);
}
