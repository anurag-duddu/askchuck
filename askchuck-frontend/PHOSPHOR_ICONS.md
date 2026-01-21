# Phosphor Icons Usage Guide

## Installation

Phosphor Icons is already installed in this project:

```bash
npm install @phosphor-icons/react
```

## Basic Usage

Import and use Phosphor Icons in your React/Next.js components:

```tsx
import { Heart, Star, User, House } from "@phosphor-icons/react";

export function MyComponent() {
  return (
    <div>
      <Heart size={32} />
      <Star size={24} weight="fill" />
      <User size={20} weight="bold" />
      <House size={16} color="#1e40af" />
    </div>
  );
}
```

## Icon Weights

Phosphor Icons supports 6 different weights:

```tsx
import { Heart } from "@phosphor-icons/react";

<Heart weight="thin" />      {/* Thinnest stroke */}
<Heart weight="light" />     {/* Light stroke */}
<Heart weight="regular" />   {/* Default weight */}
<Heart weight="bold" />      {/* Bold stroke */}
<Heart weight="fill" />      {/* Filled icon */}
<Heart weight="duotone" />   {/* Two-tone style */}
```

## Common Props

All Phosphor Icons accept these props:

- `size` (number | string): Icon size in pixels (default: 24)
- `weight` ("thin" | "light" | "regular" | "bold" | "fill" | "duotone"): Icon weight
- `color` (string): Icon color (CSS color value)
- `className` (string): CSS class names for styling
- `mirrored` (boolean): Flip icon horizontally

## Examples Used in AskChuck

### Send Button (ChatInput.tsx)
```tsx
import { PaperPlaneTilt } from "@phosphor-icons/react";

<Button>
  <PaperPlaneTilt weight="bold" size={20} />
</Button>
```

## Commonly Used Icons

Here are some icons you might find useful:

### Navigation & Actions
```tsx
import {
  House,           // Home
  MagnifyingGlass, // Search
  Gear,            // Settings
  Question,        // Help/FAQ
  SignOut,         // Logout
  ArrowLeft,       // Back
  ArrowRight,      // Forward
  X,               // Close
  List,            // Menu
} from "@phosphor-icons/react";
```

### Communication
```tsx
import {
  PaperPlaneTilt,  // Send message
  ChatCircle,      // Chat
  EnvelopeSimple,  // Email
  Bell,            // Notifications
  BookOpen,        // Documentation
} from "@phosphor-icons/react";
```

### Files & Documents
```tsx
import {
  File,            // Generic file
  FilePdf,         // PDF file
  FileText,        // Text file
  DownloadSimple,  // Download
  Upload,          // Upload
  Paperclip,       // Attachment
} from "@phosphor-icons/react";
```

### User Interface
```tsx
import {
  User,            // User profile
  Users,           // Multiple users
  Heart,           // Like/Favorite
  Star,            // Rating/Favorite
  Bookmark,        // Bookmark
  ShareNetwork,    // Share
  Copy,            // Copy to clipboard
  Check,           // Checkmark/Success
  Warning,         // Warning
  Info,            // Information
} from "@phosphor-icons/react";
```

## Integration with Tailwind CSS

Phosphor Icons work seamlessly with Tailwind:

```tsx
import { Heart } from "@phosphor-icons/react";

// Size using Tailwind
<Heart className="w-6 h-6" />

// Color using Tailwind
<Heart className="text-red-500" />

// Hover effects
<Heart className="w-6 h-6 text-gray-400 hover:text-red-500 transition-colors" />

// Combined with other Tailwind utilities
<Heart className="w-8 h-8 text-primary hover:scale-110 transition-transform cursor-pointer" />
```

## TypeScript Support

Phosphor Icons has full TypeScript support with proper type definitions:

```tsx
import { Icon } from "@phosphor-icons/react";

interface IconButtonProps {
  icon: Icon;
  label: string;
}

export function IconButton({ icon: IconComponent, label }: IconButtonProps) {
  return (
    <button>
      <IconComponent size={20} weight="bold" />
      <span>{label}</span>
    </button>
  );
}
```

## Resources

- **Official Website:** https://phosphoricons.com
- **GitHub Repository:** https://github.com/phosphor-icons/react
- **NPM Package:** https://www.npmjs.com/package/@phosphor-icons/react
- **Icon Search:** Browse all 9,000+ icons at https://phosphoricons.com

## Migration from Lucide React

If you're migrating from Lucide React, here are some common icon equivalents:

| Lucide Icon | Phosphor Icon | Notes |
|-------------|---------------|-------|
| `Send` | `PaperPlaneTilt` | Phosphor version is angled |
| `Home` | `House` | Similar appearance |
| `Search` | `MagnifyingGlass` | Exact equivalent |
| `Settings` | `Gear` | Similar functionality |
| `User` | `User` | Same name |
| `Menu` | `List` | Similar appearance |
| `X` | `X` | Same name |
| `ChevronDown` | `CaretDown` | Similar appearance |
| `Check` | `Check` | Same name |
| `Heart` | `Heart` | Same name with weight options |

## Notes

- Phosphor Icons are **free and open source** (MIT License)
- The library is **tree-shakeable** - only imported icons are bundled
- Icons are optimized SVGs with minimal bundle size impact
- All icons are designed on a 24×24 pixel grid
- The library supports both React and React Native
