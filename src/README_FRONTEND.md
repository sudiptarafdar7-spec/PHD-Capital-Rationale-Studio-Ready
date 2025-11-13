# PHD Capital — Rationale Studio (Frontend Prototype)

A comprehensive React + Tailwind CSS frontend application for generating AI-powered stock analysis PDF reports from YouTube videos.

## 🎨 Design System

**Windows 11 Glassmorphic Style**
- Backdrop blur effects with transparency
- Soft rounded corners (2xl)
- Subtle shadows and elevated cards
- Dark mode color scheme (Slate 900/800)
- Primary color: #003366 (PHD Blue)
- Accent colors: Blue (#1f77b4) and neutral greys

## 📋 Features Implemented

### ✅ Core Pages

1. **Login Page**
   - Simple authentication UI
   - Demo credentials support
   - Glassmorphic card design

2. **Dashboard**
   - Job statistics cards (Total, Completed, Failed)
   - Recent jobs list with status badges
   - Search and filter functionality
   - Quick actions (View Details, Download PDF)

3. **Media Rationale** (Full Implementation)
   - YouTube URL input form
   - 15-step pipeline progress tracker
   - Live progress monitoring
   - Step-by-step status indicators
   - Tabbed interface (Progress, Outputs, Logs)
   - File downloads and charts viewer
   - Resume from failed step functionality

4. **Activity Log**
   - Timeline-based activity display
   - Action filters and search
   - Detailed timestamps
   - Job-specific tracking

5. **Saved Rationale**
   - All generated reports list
   - Unsigned/Signed PDF management
   - Upload signed PDF functionality
   - Download actions

6. **Profile**
   - User information editing
   - Avatar upload
   - Account statistics
   - Password change option

### 👨‍💼 Admin Pages

7. **API Keys Setup**
   - OpenAI, AssemblyAI, Dhan, Google Cloud
   - Secure key input with visibility toggle
   - File upload for Google JSON
   - Status indicators
   - Encryption notice

8. **Employees Management**
   - Add/Edit/Delete employees
   - Role assignment (Admin/Employee)
   - User list with avatars
   - Contact information

9. **PDF Template Configuration**
   - Company information
   - Registration details
   - Disclaimer and disclosure text
   - Letterhead customization

10. **Upload Required Files**
    - api-scrip-master.csv
    - Company logo
    - Custom fonts
    - File validation and status

11. **Manage Channel Logos**
    - Add YouTube channels
    - Upload channel logos
    - Grid-based display
    - Delete functionality

### 🚧 Coming Soon Pages

12. **Premium Rationale** (Scaffold)
    - Form-based rationale generation
    - Stock parameters input

13. **Manual Rationale** (Scaffold)
    - Manual data entry
    - Admin-only feature

## 🏗️ Project Structure

```
/
├── components/
│   ├── Layout.tsx              # Main layout with topbar
│   ├── Sidebar.tsx             # Navigation sidebar
│   ├── StepProgressTracker.tsx # 15-step pipeline tracker
│   └── ui/                     # Shadcn components
├── pages/
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── MediaRationalePage.tsx
│   ├── PremiumRationalePage.tsx
│   ├── ManualRationalePage.tsx
│   ├── ActivityLogPage.tsx
│   ├── SavedRationalePage.tsx
│   ├── ProfilePage.tsx
│   ├── ApiKeysPage.tsx
│   ├── EmployeesPage.tsx
│   ├── PdfTemplatePage.tsx
│   ├── UploadFilesPage.tsx
│   └── ChannelLogosPage.tsx
├── lib/
│   ├── auth-context.tsx        # Authentication context
│   └── mock-data.ts            # Demo data
├── types/
│   └── index.ts                # TypeScript definitions
├── App.tsx                     # Main app component
└── styles/
    └── globals.css             # Global styles
```

## 🔧 Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Shadcn/UI** - Component library
- **Lucide React** - Icon library
- **Sonner** - Toast notifications

## 🎯 15-Step Pipeline (Media Rationale)

1. **Download Audio** - Extract from YouTube
2. **Download Captions** - Fetch auto-generated captions
3. **Transcribe Audio** - AssemblyAI with speaker labels
4. **Merge Transcripts** - Combine captions + transcript
5. **Translate** - Google Cloud Translation
6. **Detect Speakers** - AI identification (Anchor/Pradip)
7. **Filter Transcription** - Keep relevant speakers
8. **Extract Stock Mentions** - AI extraction with timestamps
9. **Map Master File** - Match to api-scrip-master.csv
10. **Convert Timestamps** - To absolute time/date
11. **Fetch CMP** - Current Market Price from Dhan API
12. **Extract Analysis** - AI-generated analysis
13. **Generate Charts** - Technical charts via mplfinance
14. **Generate PDF** - Final branded report
15. **Save / Save & Sign & Log** - Save final output and update logs

## 🔐 Security Features

- JWT-based authentication (simulated)
- Role-based access control (Admin/Employee)
- API key encryption notices
- Secure file upload indicators

## 📱 Responsive Design

- Desktop-first approach
- Mobile responsive down to 375px
- Collapsible sidebar on mobile
- Touch-friendly interfaces

## 🎨 UI Components

All Shadcn components available:
- Accordion, Alert, Avatar, Badge
- Button, Card, Checkbox, Dialog
- Dropdown Menu, Input, Select, Tabs
- Table, Toast, Tooltip, and more

## 🚀 Mock Data & Simulation

The application uses mock data to demonstrate:
- Job creation and monitoring
- Step-by-step progress tracking
- File generation and downloads
- User management
- Activity logging

## 🔄 State Management

- React Context API for authentication
- Local state management with hooks
- Toast notifications for user feedback

## 📖 Usage Notes

1. **Login**: Any email/password works (demo mode)
2. **Create Job**: Enter any YouTube URL in Media Rationale
3. **Monitor Progress**: Watch the 15-step pipeline in real-time
4. **Admin Features**: Only visible to admin role users
5. **Downloads**: Simulated - shows toast notifications

## 🎯 Production Readiness

This frontend is ready to connect to the Python FastAPI backend:

### API Integration Points
- `POST /api/v1/auth/login`
- `POST /api/v1/jobs` - Create new job
- `GET /api/v1/jobs/{job_id}` - Get job status
- `POST /api/v1/jobs/{job_id}/resume` - Resume failed job
- `GET /api/v1/dashboard/summary` - Dashboard stats
- `POST /api/v1/admin/api-keys` - Save API keys
- All other CRUD endpoints for users, files, etc.

### WebSocket Support
Add WebSocket connection for real-time step updates:
```typescript
const ws = new WebSocket('ws://backend/jobs/{job_id}/progress');
ws.onmessage = (event) => {
  updateStepProgress(JSON.parse(event.data));
};
```

## 🎨 Design Credits

- Logo: PHD Capital branding
- Icons: Lucide React
- Color Scheme: Custom Windows 11 inspired
- Typography: System fonts with fallbacks

## 📝 Next Steps for Production

1. Connect to FastAPI backend
2. Implement real authentication with JWT
3. Add WebSocket for live progress
4. Implement actual file downloads
5. Add PDF viewer component
6. Implement chart gallery
7. Add CSV table viewer
8. Set up error boundaries
9. Add loading states
10. Implement pagination

## 💡 Key Features

- ✅ Complete UI for all 15 pipeline steps
- ✅ Real-time progress simulation
- ✅ Admin panel with all configuration pages
- ✅ Responsive glassmorphic design
- ✅ Role-based navigation
- ✅ Toast notifications
- ✅ Form validation
- ✅ Mock data for demonstration

## 🌟 Highlights

- **Production-ready UI** - Ready to connect to backend
- **Modular architecture** - Easy to maintain and extend
- **Type-safe** - Full TypeScript coverage
- **Accessible** - ARIA labels and keyboard navigation
- **Beautiful** - Windows 11 glassmorphic design
- **Responsive** - Works on all screen sizes

---

**Built for PHD Capital — Transforming YouTube analysis into professional PDF reports**
