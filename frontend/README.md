# Nyaya Marga Frontend

A Next.js TypeScript frontend for the Nyaya Marga legal document processing system.

## Features

- 📄 PDF document upload with case number tracking
- 🔍 Real-time NLP entity extraction display
- 📊 Extracted entities with confidence scores and page locations
- 📋 AI-generated administrative action plans
- 🎯 Progress tracking through multi-step workflow
- 🔄 Automatic polling for async backend processing

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe code
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client for API integration

## Setup

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Set environment variables
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Development

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm start        # Start production server
npm run lint     # Run ESLint
```

## Docker

Build and run with Docker:

```bash
docker build -t nyaya-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 nyaya-frontend
```

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with header/footer
│   ├── page.tsx            # Main application logic
│   └── globals.css         # Global styles
├── components/
│   ├── PdfUploadForm.tsx   # File upload component
│   ├── EntityList.tsx      # Entity display component
│   ├── ActionPlanDisplay.tsx # Action plan visualization
│   └── LoadingSpinner.tsx  # Loading indicator
├── lib/
│   ├── api.ts              # API client and utilities
│   └── types.ts            # TypeScript interfaces
└── public/                 # Static assets
```

## API Integration

The frontend communicates with the Nyaya Marga backend API:

### Endpoints Used

- `POST /api/v1/cases/upload` - Upload and process PDF
- `GET /api/v1/cases/{case_id}/status` - Poll extraction status
- `GET /api/v1/cases/{case_id}/action-plan` - Retrieve action plan
- `POST /api/v1/cases/{case_id}/generate-action-plan` - Trigger plan generation

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API base URL (default: http://localhost:8000)

## Workflow

1. **Upload** - User uploads PDF with case number
2. **Processing** - Backend extracts text and runs NLP
3. **Review** - Display extracted entities with confidence scores
4. **Action Plan** - Generate and display administrative action plan

## Error Handling

The app includes comprehensive error handling with user-friendly messages for:
- File upload failures
- API errors
- Processing timeouts
- Validation errors
