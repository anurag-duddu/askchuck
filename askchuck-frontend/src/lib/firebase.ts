import { initializeApp, getApps } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getFirestore } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyCJkXj80R4pihbtC15gz6hM-_pEqNmgFbw", // pragma: allowlist secret
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "askchuck.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "askchuck",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "askchuck.appspot.com",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "725776442176",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:725776442176:web:4f3e022ad05e610c1a50a5",
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || "G-43FCGW5L28"
}

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0]
export const auth = getAuth(app)
export const db = getFirestore(app)
export default app
