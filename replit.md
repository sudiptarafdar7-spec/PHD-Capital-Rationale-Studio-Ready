# PHD Capital Rationale Studio

## Overview
PHD Capital Rationale Studio is a full-stack web application designed to automate the generation of professional financial rationale reports. It features three primary tools: Media Rationale (YouTube video analysis), Premium Rationale (AI-powered text analysis), and Manual Rationale (manual data entry with autocomplete). The application aims to enhance efficiency in financial reporting by converting multimedia content and structured data into actionable financial insights.

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
    - **Media Rationale Pipeline**: A 14-step process for YouTube videos (extraction, transcription, translation, analysis, report generation). Includes a dual-method fallback architecture for audio download (RapidAPI + yt-dlp) and a RapidAPI-based caption download, both handling universal YouTube URL formats.
    - **Premium Rationale Pipeline**: An 8-step process for generating reports from text input (stock data fetching, technical/fundamental analysis, PDF generation). Step 3 includes intelligent CMP fallback (intraday price during market hours, historical closing price otherwise). Step 4 includes try-first-then-fallback pattern for chart generation (attempts exact date/time first, falls back to last trading day's 3:30 PM close if data unavailable - handles weekends/holidays).
    - **Manual Rationale v2 Pipeline**: Redesigned 3-step process (Fetch CMP → Generate Charts → Generate PDF) with thread-based async orchestration.
        - **Fetch CMP**: Fetches Current Market Price from Dhan API with intelligent market hours handling (intraday price during market hours, historical closing price otherwise). Includes automatic API key decryption.
        - **Generate Charts**: Standalone chart generation with Dhan API for candlestick, moving averages, RSI, and volume.
        - **Generate PDF**: Professional PDF generation with premium blue theme, company letterhead, platform branding, charts, rationale sections, and disclaimer. Secure PDF viewing and download with JWT authentication.
        - **Master Data Enrichment**: Server-side enrichment from uploaded master CSV for stock data.
    - **Stock Autocomplete**: Intelligent stock symbol autocomplete using master CSV data.
    - **Date Format Normalization**: Handles DD/MM/YYYY and YYYY-MM-DD formats, normalizing to ISO.
- **System Design Choices**:
    - **Modular API**: Endpoints are organized by feature.
    - **Pipeline-driven Processing**: Sequential analysis for both video and text.
    - **Database Schema**: Unified `jobs` and `saved_rationale` tables for multi-tool compatibility, alongside tables for `users`, `api_keys`, `pdf_template`, `uploaded_files`, `channels`, `job_steps`, and `activity_logs`.
    - **Status System**: Comprehensive status tracking for jobs and job steps.
    - **File Storage**: Secure server-side storage using UUID-based filenames.
    - **Deployment**: Optimized for VPS environments with automated setup, including git safe directory configurations.

## AI Configuration
- **Dual AI Provider Architecture**:
    - **Gemini (Google AI)**: Used for Step 8 (Stock Extraction) - gemini-2.5-pro model via REST API (most capable model with advanced reasoning)
    - **OpenAI (GPT-4o)**: Used for other pipeline steps (analysis extraction, content generation)
- **Centralized Configuration**: 
    - `backend/utils/gemini_config.py` provides Gemini settings for Step 8
    - `backend/utils/openai_config.py` provides OpenAI settings for other steps
- **Expert Persona**: All AI responses behave as a SEBI-registered Research Analyst with 15+ years of experience
- **Pipeline Integration**:
    - Step 8 (Stock Extraction): Uses gemini-2.5-pro with `get_stock_extraction_prompt()` for accurate NSE symbol mapping
        - **4-Chunk Processing**: Transcript split into 4 chunks for comprehensive stock detection
        - **Intelligent Spelling Correction**: 50+ transcription error mappings (Suzuelon→Suzlon, Sujalan→Suzlon, etc.)
        - **Google Search Grounding**: For unclear transcription errors (Cera Bank, Wari, NIBA), uses Gemini with Google Search to find correct NSE stock names
        - **Symbol Normalization**: Deduplication and standardization of NSE symbols
    - Step 12 (Analysis Extraction): Uses OpenAI GPT-4o with `get_analysis_extraction_prompt()` for professional rationale extraction
    - Premium Step 1 (CSV Generation): Uses OpenAI GPT-4o with `get_premium_csv_prompt()` for structured stock call parsing
    - Premium Step 7 (Analysis Generation): Uses OpenAI GPT-4o with `get_premium_analysis_prompt()` for SEBI-compliant investment rationales
- **Temperature Settings**: 0.0-0.3 for extraction tasks, 0.5-0.7 for analysis generation
- **API Key Management**: Both Gemini and OpenAI API keys are managed through Settings → API Keys

## External Dependencies
- **Database**: PostgreSQL (via Neon)
- **Authentication**: Flask-JWT-Extended, bcrypt
- **CORS Management**: Flask-CORS
- **Video Processing**: `yt-dlp`, `ffmpeg-python`, RapidAPI (youtube-mp36, Video Transcript Scraper)
- **Transcription**: AssemblyAI API
- **Data Processing**: pandas, numpy, rapidfuzz
- **Translation**: Google Cloud Translation API
- **UI Icons**: Lucide React
- **AI Analysis**: OpenAI API (GPT-4o) with centralized expert analyst configuration
- **Financial Data**: Dhan API, Yahoo Finance
- **PDF Generation**: ReportLab
- **Image Processing**: Pillow (PIL)