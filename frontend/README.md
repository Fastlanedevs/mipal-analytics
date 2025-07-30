# mipal-analytics front end

# Mipal Analytics Frontend

A modern React-based frontend application for Mipal Analytics, built with Next.js, TypeScript, and Tailwind CSS.

## 🚀 Quick Start

### Prerequisites

- **Node.js** (v18 or higher)
- **npm** or **yarn** package manager
- **Git**

### Installation

1. **Clone the repository** (if not already done):

   ```bash
   git clone <repository-url>
   cd mipal-analytics/frontend
   ```

2. **Install dependencies**:

   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables**:

   ```bash
   cp .env.example .env.local
   ```

   Edit `.env.local` with your configuration:

   ```env
   # Next.js Configuration
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=your_nextauth_secret_here

   # Backend API URL
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

   # App Configuration
   NEXT_PUBLIC_APP_URL=http://localhost:3000

   # Database (if needed)
   DATABASE_URL=postgresql://mipal:mipal123@localhost:5432/mipal

   # Redis (if needed)
   REDIS_URL=redis://localhost:6379
   ```

### Development Server

Start the development server:

```bash
npm run dev
# or
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Production Build

Build the application for production:

```bash
npm run build
# or
yarn build
```

Start the production server:

```bash
npm start
# or
yarn start
```

## 🛠️ Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking
- `npm run test` - Run tests (if configured)

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 13+ app directory
│   │   ├── (protected)/        # Protected routes
│   │   ├── api/                # API routes
│   │   └── auth/               # Authentication pages
│   ├── components/             # Reusable components
│   │   ├── ui/                 # Base UI components
│   │   ├── common/             # Common components
│   │   └── modals/             # Modal components
│   ├── store/                  # Redux store
│   │   ├── slices/             # Redux slices
│   │   └── services/           # RTK Query services
│   ├── hooks/                  # Custom React hooks
│   ├── types/                  # TypeScript type definitions
│   ├── lib/                    # Utility libraries
│   └── styles/                 # Global styles
├── public/                     # Static assets
├── messages/                   # Internationalization files
└── docker/                     # Docker configuration
```

## 🔧 Key Technologies

- **Next.js 13+** - React framework with app directory
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Redux Toolkit** - State management
- **RTK Query** - Data fetching and caching
- **NextAuth.js** - Authentication
- **shadcn/ui** - UI component library
- **Lucide React** - Icon library

## 🔐 Authentication

The application uses NextAuth.js for authentication with the following providers:

- **Credentials** (Email/Password)

### Environment Variables for Auth

```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret_here
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## 🗄️ Database Integration

Currently supports:

- **PostgreSQL** - Primary database integration

### PostgreSQL Configuration

```env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

## 🐳 Docker Support

### Development with Docker

```bash
# Build and run with docker-compose
docker-compose up --build

# Or build and run individually
docker build -f docker/Dockerfile-dev -t mipal-frontend-dev .
docker run -p 3000:3000 mipal-frontend-dev
```

### Production with Docker

```bash
# Build production image
docker build -f docker/Dockerfile -t mipal-frontend .

# Run production container
docker run -p 3000:3000 mipal-frontend
```

## 🌐 Internationalization

The application supports multiple languages using `next-intl`:

- English (en)
- Spanish (es)
- French (fr)

Language files are located in `messages/` directory.

## 🎨 Styling

The application uses:

- **Tailwind CSS** for utility-first styling
- **shadcn/ui** for pre-built components
- **CSS Modules** for component-specific styles

### Custom CSS Classes

```css
/* Global styles in styles/globals.css */
/* Component styles in respective .module.css files */
```

## 📱 Responsive Design

The application is fully responsive and supports:

- Desktop (1024px+)
- Tablet (768px - 1023px)
- Mobile (320px - 767px)

## 🔍 Development Tools

### Code Quality

- **ESLint** - Code linting
- **Prettier** - Code formatting
- **TypeScript** - Type checking

### Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## 🚨 Troubleshooting

### Common Issues

1. **Port 3000 already in use**:

   ```bash
   # Kill process using port 3000
   lsof -ti:3000 | xargs kill -9
   ```

2. **Node modules issues**:

   ```bash
   # Clear node modules and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Environment variables not loading**:

   - Ensure `.env.local` file exists
   - Restart the development server
   - Check variable names match exactly

4. **Build errors**:
   ```bash
   # Clear Next.js cache
   rm -rf .next
   npm run build
   ```

### Development Tips

- Use `npm run type-check` to check TypeScript types
- Use `npm run lint` to check code quality
- Check browser console for runtime errors
- Use React Developer Tools for debugging

## 📞 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the backend documentation
3. Check the project issues on GitHub

## 📄 License

This project is proprietary software. All rights reserved.

---

**Happy coding! 🚀**
