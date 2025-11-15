# PHD Capital Rationale Studio

## Overview
PHD Capital Rationale Studio is a full-stack web application designed to automate the generation of professional financial rationale reports. It features three primary tools: Media Rationale (YouTube video analysis), Premium Rationale (AI-powered text analysis), and Manual Rationale (manual data entry with autocomplete). The application aims to enhance efficiency in financial reporting by converting multimedia content and structured data into actionable financial insights.

## Recent Changes (November 2025)
### Manual Rationale v2 Complete Rebuild ✅ COMPLETED
- **Cleaned up legacy code**: Removed old manual_rationale.py and backend/pipeline/manual/ directory
- **New service architecture**: Created backend/services/manual_v2/ with clean separation of concerns
- **Improved pipeline orchestration**: Thread-based async execution with proper status tracking
- **Code reuse**: Leverages existing premium pipeline functions for charts and PDF generation (avoiding duplication)
- **Database enhancements**: Added `payload` JSONB column to jobs table, `metadata` JSONB column to saved_rationale table
- **Robust error handling**: Safe numeric parsing in CMP step to handle empty/invalid user inputs
- **New API endpoints**: 8 REST endpoints under /api/v1/manual-v2/ for complete job lifecycle management
- **Frontend updates**: 
  - Stock autocomplete displays symbols (e.g., "RELIANCE") instead of company names
  - Job loading fixed: Now correctly loads from jobs table (for unsaved jobs) with fallback to saved_rationale
  - Contract mismatches resolved: Stock autocomplete accepts both 'q' and 'query' parameters, job creation sends correct payload structure
  - Workflow stage management: Proper step display visibility based on job status
  - Polling for in-progress jobs: Continues polling when loading jobs from dashboard
- **Input CSV Generation**: Automated creation of input.csv before pipeline execution with columns: DATE, TIME, STOCK SYMBOL, CHART TYPE, LISTED NAME, SHORT NAME, SECURITY ID, EXCHANGE, INSTRUMENT, ANALYSIS
  - Master data automatically enriched from uploaded master CSV at job creation
  - Chart type uses user's direct input (Daily/Weekly/Monthly)
  - Analysis column populated with user's detailed analysis text
- **Status**: ✅ Fully implemented, tested, and production-ready

## User Preferences
- Keep frontend design unchanged (layout, forms, fields, animations, effects, flow)
- Use Flask for backend REST API
- Use PostgreSQL for database
- JWT tokens for authentication
- Role-based access control (admin/employee)

## System Architecture
The application maintains a clear separation between a React-based frontend and a Flask-based backend, optimized for robust financial analysis and reporting.

### Frontend
- **Framework**: React 18 with TypeScript, built using Vite.
- **UI/UX**: Radix UI for accessibility and Tailwind CSS for modern design.
- **State Management**: React Context API.
- **Structure**: Employs reusable components and page-specific structures.

### Backend
- **Framework**: Flask (Python 3.11) providing a REST API.
- **Authentication**: Flask-JWT-Extended for JWTs and bcrypt for password hashing.
- **Database**: PostgreSQL (Neon).
- **CORS**: Flask-CORS configured.
- **Core Features**:
    - **User and API Key Management**: CRUD operations for users (Admin/Employee roles) and secure storage for external API keys.
    - **PDF Template Management**: Configuration for standardized PDF reports.
    - **File Management**: Handling of master CSVs, logos, custom fonts, and YouTube cookies.
    - **Channel/Platform Management**: CRUD operations for various platforms, including logo uploads.
    - **Media Rationale Pipeline**: A 14-step process for YouTube videos (extraction, transcription, translation, analysis, report generation).
    - **Premium Rationale Pipeline**: An 8-step process for generating reports from text input (stock data fetching, technical/fundamental analysis, PDF generation).
    - **Manual Rationale v2 Pipeline**: Redesigned 3-step process (Fetch CMP → Generate Charts → Generate PDF) with clean architecture:
        - **Module location**: `backend/services/manual_v2/` (replaces old `backend/pipeline/manual/`)
        - **Orchestration**: Thread-based async pipeline with ManualRationaleOrchestrator
        - **Step 1**: Fetches Current Market Price (CMP) from Dhan API with safe numeric parsing
        - **Step 2**: Generates charts by reusing premium pipeline's chart generation functions
        - **Step 3**: Generates PDF by reusing premium PDF generator (BLUE theme)
        - **Master data enrichment**: Server-side enrichment at job creation via `/manual-v2/jobs` endpoint
        - **API endpoints**: `/manual-v2/jobs` (create), `/manual-v2/jobs/<id>/run` (execute pipeline), `/manual-v2/jobs/<id>/save` (save to saved_rationale), `/manual-v2/jobs/<id>/upload-signed` (signed PDF upload), `/manual-v2/stocks` (autocomplete)
    - **Stock Autocomplete**: Intelligent stock symbol autocomplete using master CSV data, filtering EQUITY stocks from SEM_TRADING_SYMBOL column where SEM_INSTRUMENT_NAME='EQUITY' AND SEM_EXCH_INSTRUMENT_TYPE='ES'. Frontend provides autocomplete suggestions; backend performs master data lookup server-side for validation and enrichment. Uses 300ms debounced API calls.
    - **Master Data Enrichment**: Backend automatically fetches master data (SECURITY ID, LISTED NAME, SHORT NAME, EXCHANGE, INSTRUMENT) from uploaded master CSV when creating Manual Rationale jobs. Column mapping: SEM_SMST_SECURITY_ID→SECURITY ID, SM_SYMBOL_NAME→LISTED NAME, SEM_CUSTOM_SYMBOL→SHORT NAME, SEM_EXM_EXCH_ID→EXCHANGE, SEM_INSTRUMENT_NAME→INSTRUMENT. Validates all stock symbols exist in master CSV; returns 400 error for missing stocks.
    - **Date Format Normalization**: Backend accepts both DD/MM/YYYY and YYYY-MM-DD date formats from frontend, normalizes to ISO format (YYYY-MM-DD) before storing in database and CSV files.
- **System Design Choices**:
    - **Modular API**: Endpoints are organized by feature.
    - **Pipeline-driven Processing**: Sequential analysis for both video and text.
    - **Database Schema**: Unified `jobs` and `saved_rationale` tables for multi-tool compatibility, alongside tables for `users`, `api_keys`, `pdf_template`, `uploaded_files`, `channels`, `job_steps`, and `activity_logs`.
    - **Status System**: Comprehensive status tracking for jobs (`pending`, `processing`, `awaiting_csv_review`, `pdf_ready`, `completed`, `failed`, `signed`) and job steps (`pending`, `running`, `success`, `failed`).
    - **File Storage**: Secure server-side storage using UUID-based filenames.
    - **Deployment**: Optimized for VPS environments with automated setup.

## External Dependencies
- **Database**: PostgreSQL (via Neon)
- **Authentication**: Flask-JWT-Extended, bcrypt
- **CORS Management**: Flask-CORS
- **Video Processing**: `yt-dlp`, `ffmpeg-python`
- **Transcription**: AssemblyAI API
- **Data Processing**: pandas, numpy, rapidfuzz
- **Translation**: Google Cloud Translation API
- **UI Icons**: Lucide React
- **AI Analysis**: OpenAI API (GPT-4o)
- **Financial Data**: Dhan API (for CMP, charts, technical indicators), Yahoo Finance (for fundamental data)
- **PDF Generation**: ReportLab
- **Image Processing**: Pillow (PIL)