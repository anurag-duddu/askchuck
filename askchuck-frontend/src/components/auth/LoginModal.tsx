"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  limitHit?: boolean;
}

export function LoginModal({ open, onClose, limitHit = false }: LoginModalProps) {
  const { signInWithGoogle, signInWithEmail } = useAuth();

  const [showEmailForm, setShowEmailForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const overlayRef = useRef<HTMLDivElement>(null);
  const firstFocusRef = useRef<HTMLButtonElement>(null);

  // Focus management on open
  useEffect(() => {
    if (open) {
      setTimeout(() => firstFocusRef.current?.focus(), 50);
    }
  }, [open]);

  // Close on Escape (only if not limit-hit)
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !limitHit) onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, limitHit, onClose]);

  if (!open) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (!limitHit && e.target === overlayRef.current) onClose();
  };

  const handleGoogle = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await signInWithGoogle();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await signInWithEmail(email, password);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign-in failed.";
      // Surface friendly Firebase error messages
      if (message.includes("wrong-password") || message.includes("invalid-credential")) {
        setError("Incorrect password. Please try again.");
      } else if (message.includes("invalid-email")) {
        setError("Please enter a valid email address.");
      } else if (message.includes("weak-password")) {
        setError("Password must be at least 6 characters.");
      } else {
        setError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-modal-heading"
    >
      <div className="relative w-full max-w-md mx-4 bg-card border border-border rounded-sm shadow-lg p-8">
        {/* Close button — only shown when not limit-hit */}
        {!limitHit && (
          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Heading */}
        <div className="mb-6 space-y-2">
          <h2
            id="login-modal-heading"
            className="text-2xl font-serif text-foreground tracking-tight"
          >
            {limitHit ? "You've used your 5 free questions" : "Continue Exploring"}
          </h2>
          <p className="text-sm text-muted-foreground font-serif italic leading-relaxed">
            Sign in to save your conversations and ask unlimited questions
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-sm border border-destructive/50 bg-destructive/10 text-sm text-destructive font-serif">
            {error}
          </div>
        )}

        {/* Google sign-in (primary) */}
        <button
          ref={firstFocusRef}
          onClick={handleGoogle}
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-3 px-6 py-3 border border-border rounded-sm bg-card hover:border-primary hover:bg-accent/10 transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {/* Google "G" icon */}
          <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span className="text-sm font-serif text-foreground">
            {isSubmitting ? "Signing in..." : "Continue with Google"}
          </span>
        </button>

        {/* Divider */}
        <div className="my-5 flex items-center gap-3">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-muted-foreground font-serif uppercase tracking-wider">
            or
          </span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Email toggle / form */}
        {!showEmailForm ? (
          <button
            onClick={() => setShowEmailForm(true)}
            className="w-full px-6 py-3 text-sm font-serif text-muted-foreground border border-border rounded-sm hover:border-primary hover:text-foreground hover:bg-accent/10 transition-all duration-300"
          >
            Sign in with email
          </button>
        ) : (
          <form onSubmit={handleEmailSubmit} className="space-y-3">
            <div>
              <label
                htmlFor="login-email"
                className="block text-xs font-serif uppercase tracking-wider text-muted-foreground mb-1"
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 text-sm font-serif bg-background border border-border rounded-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/60"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label
                htmlFor="login-password"
                className="block text-xs font-serif uppercase tracking-wider text-muted-foreground mb-1"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 text-sm font-serif bg-background border border-border rounded-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/60"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full px-6 py-3 text-sm font-serif text-primary-foreground bg-primary rounded-sm hover:bg-primary/90 transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Signing in..." : "Continue with Email"}
            </button>
            <p className="text-xs text-muted-foreground text-center font-serif">
              New here? We&apos;ll create your account automatically.
            </p>
          </form>
        )}

        {/* Footer note */}
        <p className="mt-6 text-xs text-muted-foreground/70 text-center font-serif">
          By signing in, you agree to explore Charles Owen&apos;s archive freely.
        </p>
      </div>
    </div>
  );
}
