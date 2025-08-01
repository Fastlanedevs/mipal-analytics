# MIPAL Analytics Frontend

A modern, responsive frontend built with Next.js 14 and TypeScript, providing an intuitive interface for conversational analytics and data visualization.

## 🚀 Features

### 🎨 Modern UI/UX
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Component Library**: Radix UI primitives with custom styling
- **Dark/Light Mode**: Theme switching with next-themes
- **Rich Text Editor**: TipTap editor with markdown support

### 🤖 Conversational Interface
- **Real-time Chat**: WebSocket-based streaming conversations
- **AI-Powered Analytics**: Natural language queries for data analysis
- **Interactive Charts**: Dynamic visualization with Recharts and Vega-Lite
- **Code Execution**: Syntax highlighting and interactive code blocks

### 📊 Dashboard & Analytics
- **Drag & Drop Dashboards**: Customizable dashboard layouts
- **Chart Builder**: AI-assisted chart creation and customization
- **Data Visualization**: Multiple chart types and interactive features
- **Export Capabilities**: PDF and various format exports

### 🔐 Authentication & Security
- **NextAuth.js Integration**: Multiple authentication providers
- **JWT Token Management**: Secure token handling and refresh
- **Role-based Access**: Organization and user permission system
- **Session Management**: Persistent authentication state

## 🛠️ Technology Stack

### Core Framework
- **Next.js 14**: App Router with Server Components
- **TypeScript 5+**: Full type safety
- **React 18**: Latest React features

### UI & Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives
- **Framer Motion**: Smooth animations and transitions
- **Lucide React**: Beautiful icon library

### State Management
- **Redux Toolkit**: Predictable state management
- **RTK Query**: Efficient data fetching and caching
- **Redux Persist**: State persistence across sessions

### Data Visualization
- **Recharts**: Composable charting library
- **Vega-Lite**: Grammar of interactive graphics
- **React Vega**: Vega-Lite integration for React

### Rich Content
- **TipTap**: Extensible rich text editor
- **React Markdown**: Markdown rendering with extensions
- **KaTeX**: Mathematical notation rendering
- **Mermaid**: Diagram and flowchart generation

## 📋 Prerequisites

- Node.js 18+
- npm or yarn
- Backend API server running (see [backend README](../backend/README.md))

## 🔧 Installation

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   
   Create a `.env.local` file:
   ```bash
   # API Configuration
   NEXT_PUBLIC_API_URL=http://localhost:8000
   
   # Authentication
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=your_nextauth_secret_key
   
   # Optional: Analytics
   NEXT_PUBLIC_POSTHOG_KEY=your_posthog_key
   NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
   
   # Optional: Sentry Error Tracking
   SENTRY_DSN=your_sentry_dsn
   ```

## 🚀 Running the Application

### Development Mode
```bash
npm run dev
```
Visit `http://localhost:3000`

### Production Build
```bash
npm run build
npm run start
```

### Code Quality
```bash
npm run lint          # ESLint checking
npm run format        # Prettier formatting
npm run format:check  # Check formatting
```

## 🏗️ Project Structure

```
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # Authentication pages
│   │   ├── (dashboard)/       # Dashboard pages
│   │   ├── globals.css        # Global styles
│   │   └── layout.tsx         # Root layout
│   │
│   ├── components/            # Reusable components
│   │   ├── ui/               # Base UI components (Radix)
│   │   ├── forms/            # Form components
│   │   ├── charts/           # Chart components
│   │   ├── chat/             # Chat interface
│   │   └── layout/           # Layout components
│   │
│   ├── store/                # Redux store
│   │   ├── slices/           # Redux slices
│   │   ├── api/              # RTK Query APIs
│   │   └── store.ts          # Store configuration
│   │
│   ├── lib/                  # Utilities and configurations
│   │   ├── auth.config.ts    # NextAuth configuration
│   │   ├── utils.ts          # Utility functions
│   │   └── constants.ts      # App constants
│   │
│   ├── hooks/                # Custom React hooks
│   ├── types/                # TypeScript type definitions
│   └── styles/               # Additional stylesheets
│
├── public/                   # Static assets
├── next.config.js           # Next.js configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration
```

## 🎨 Component Architecture

### UI Components
Built on Radix UI primitives with custom styling:
- **Buttons**: Various sizes and variants
- **Forms**: Input fields, selects, checkboxes
- **Modals**: Dialogs, alerts, popovers
- **Navigation**: Tabs, dropdowns, breadcrumbs

### Chart Components
- **ChartBuilder**: Interactive chart creation
- **VegaChart**: Vega-Lite integration
- **RechartsWrapper**: Recharts components
- **ChartExport**: Export functionality

### Chat Interface
- **MessageList**: Conversation display
- **MessageInput**: Rich text input
- **StreamingResponse**: Real-time message updates
- **CodeBlock**: Syntax highlighted code

## 🔌 API Integration

### RTK Query Setup
```typescript
// Example API slice
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: process.env.NEXT_PUBLIC_API_URL,
    prepareHeaders: (headers, { getState }) => {
      const token = selectCurrentToken(getState())
      if (token) {
        headers.set('authorization', `Bearer ${token}`)
      }
      return headers
    },
  }),
  endpoints: (builder) => ({
    // Define endpoints
  }),
})
```

### WebSocket Integration
```typescript
// WebSocket hook for real-time chat
export const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  
  useEffect(() => {
    const ws = new WebSocket(url)
    setSocket(ws)
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      setMessages(prev => [...prev, message])
    }
    
    return () => ws.close()
  }, [url])
  
  return { socket, messages }
}
```

## 🎯 Key Features Implementation

### Authentication Flow
1. **Login/Register**: NextAuth.js integration
2. **Token Management**: Automatic refresh handling
3. **Protected Routes**: Middleware-based protection
4. **Session Persistence**: Redux persist integration

### Dashboard Creation
1. **Drag & Drop**: React DnD kit integration
2. **Widget System**: Modular dashboard components
3. **Real-time Updates**: WebSocket-based data sync
4. **Responsive Layouts**: Mobile-optimized grids

### Chart Generation
1. **AI Integration**: Backend chart generation API
2. **Interactive Editing**: Real-time chart updates
3. **Export Options**: Multiple format support
4. **Responsive Design**: Mobile-friendly charts

## 🧪 Testing

```bash
# Run tests (when implemented)
npm test

# Run E2E tests (when implemented)
npm run test:e2e
```

## 🚀 Deployment

### Vercel (Recommended)
```bash
# Deploy to Vercel
vercel --prod
```

### Docker
```bash
# Build Docker image
docker build -t mipal-frontend .

# Run container
docker run -p 3000:3000 mipal-frontend
```

### Environment Variables for Production
```bash
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXTAUTH_URL=https://your-frontend-domain.com
NEXTAUTH_SECRET=your_production_secret
```

## 🤝 Contributing

### Development Guidelines
1. **Component Structure**: Follow the established pattern
2. **TypeScript**: Maintain strict type safety
3. **Styling**: Use Tailwind CSS classes
4. **State Management**: Use Redux for complex state
5. **API Calls**: Use RTK Query for data fetching

### Code Style
- **ESLint**: Follow the configured rules
- **Prettier**: Auto-format on save
- **Naming**: Use descriptive component names
- **File Organization**: Group related components

### Pull Request Process
1. Create feature branch from `main`
2. Implement changes with tests
3. Run linting and formatting
4. Submit PR with clear description

## 🐛 Troubleshooting

### Common Issues

**Build Errors**
```bash
# Clear Next.js cache
rm -rf .next
npm run build
```

**Type Errors**
```bash
# Check TypeScript
npx tsc --noEmit
```

**Styling Issues**
```bash
# Rebuild Tailwind
npm run build:css
```

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.

## 🗺️ Roadmap

### Current (v0.1.0)
- [x] Core chat interface
- [x] Dashboard creation
- [x] Chart generation
- [x] Authentication system
- [x] Responsive design

### Next Release (v0.2.0)
- [ ] Mobile app (React Native)
- [ ] Offline functionality
- [ ] Enhanced collaboration
- [ ] Advanced chart customization
- [ ] Plugin marketplace

### Future
- [ ] Multi-language support
- [ ] Custom theme builder
- [ ] Advanced animations
- [ ] PWA capabilities
- [ ] Voice interface

---

**Built with ❤️ using Next.js and TypeScript**

*For backend documentation, see [../backend/README.md](../backend/README.md)*
*For full project overview, see [../README.md](../README.md)*