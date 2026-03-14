# React Frontend

Frontend application for Adobe Experience League Chatbot, migrated from Streamlit.

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### 4. Run Tests

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/         # Page components
│   ├── services/       # API services
│   ├── store/         # State management (Zustand)
│   ├── theme.ts       # Material-UI theme
│   └── main.tsx       # Entry point
├── public/            # Static assets
└── package.json
```

## Features

- ✅ Chat interface with message history
- ✅ Query validation
- ✅ Material-UI components
- ✅ React Router for navigation
- ✅ Zustand for state management
- ✅ TypeScript for type safety

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

