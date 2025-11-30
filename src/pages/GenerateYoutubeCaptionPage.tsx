import React, { useState } from 'react';
import { Captions, Link2, Globe, Download, Loader2, RefreshCw, Trash2, Clock, AlertCircle } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { API_ENDPOINTS, getAuthHeaders } from '../lib/api-config';
import { useAuth } from '../lib/auth-context';

interface GenerateYoutubeCaptionPageProps {
  onNavigate?: (page: string) => void;
}

interface Language {
  code: string;
  name: string;
}

interface Caption {
  timestamp: string;
  start_ms: number;
  text: string;
}

interface CaptionData {
  captionId: string;
  captions: Caption[];
  rawText: string;
  language: string;
  downloadUrl: string;
}

export default function GenerateYoutubeCaptionPage({ onNavigate }: GenerateYoutubeCaptionPageProps) {
  const { token } = useAuth();
  
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [languages, setLanguages] = useState<Language[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [videoId, setVideoId] = useState<string | null>(null);
  
  const [isFetchingLanguages, setIsFetchingLanguages] = useState(false);
  const [isFetchingCaptions, setIsFetchingCaptions] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  
  const [captionData, setCaptionData] = useState<CaptionData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFetchLanguages = async () => {
    if (!youtubeUrl.trim()) {
      toast.error('Please enter a YouTube URL');
      return;
    }

    setIsFetchingLanguages(true);
    setError(null);
    setLanguages([]);
    setSelectedLanguage('');
    setCaptionData(null);
    setVideoId(null);

    try {
      const response = await fetch(API_ENDPOINTS.youtubeCaption.languages, {
        method: 'POST',
        headers: getAuthHeaders(token || ''),
        body: JSON.stringify({ youtube_url: youtubeUrl }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to fetch available languages');
      }

      setLanguages(data.languages || []);
      setVideoId(data.video_id);
      
      if (data.languages && data.languages.length > 0) {
        setSelectedLanguage(data.languages[0].code);
        toast.success(`Found ${data.languages.length} available language(s)`);
      } else {
        toast.warning('No captions available for this video');
      }
    } catch (error: any) {
      console.error('Error fetching languages:', error);
      setError(error.message || 'Failed to fetch available languages');
      toast.error(error.message || 'Failed to fetch available languages');
    } finally {
      setIsFetchingLanguages(false);
    }
  };

  const handleFetchCaptions = async () => {
    if (!youtubeUrl.trim()) {
      toast.error('Please enter a YouTube URL');
      return;
    }

    setIsFetchingCaptions(true);
    setError(null);
    setCaptionData(null);

    try {
      const response = await fetch(API_ENDPOINTS.youtubeCaption.fetch, {
        method: 'POST',
        headers: getAuthHeaders(token || ''),
        body: JSON.stringify({
          youtube_url: youtubeUrl,
          language: selectedLanguage || undefined,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to fetch captions');
      }

      setCaptionData({
        captionId: data.caption_id,
        captions: data.captions || [],
        rawText: data.raw_text || '',
        language: data.language || 'auto',
        downloadUrl: data.download_url,
      });

      toast.success(`Fetched ${data.captions?.length || 0} caption segments`);
    } catch (error: any) {
      console.error('Error fetching captions:', error);
      setError(error.message || 'Failed to fetch captions');
      toast.error(error.message || 'Failed to fetch captions');
    } finally {
      setIsFetchingCaptions(false);
    }
  };

  const handleDownload = async () => {
    if (!captionData?.captionId) return;

    setIsDownloading(true);

    try {
      const response = await fetch(API_ENDPOINTS.youtubeCaption.download(captionData.captionId), {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download caption file');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `youtube_caption_${captionData.captionId}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast.success('Caption file downloaded successfully!');

      setCaptionData(null);
      setLanguages([]);
      setSelectedLanguage('');
      setVideoId(null);
    } catch (error: any) {
      console.error('Error downloading caption:', error);
      toast.error(error.message || 'Failed to download caption file');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleClear = async () => {
    if (captionData?.captionId) {
      try {
        await fetch(API_ENDPOINTS.youtubeCaption.clear(captionData.captionId), {
          method: 'DELETE',
          headers: getAuthHeaders(token || ''),
        });
      } catch (e) {
        console.error('Error clearing caption:', e);
      }
    }

    setCaptionData(null);
    setLanguages([]);
    setSelectedLanguage('');
    setVideoId(null);
    setError(null);
  };

  const handleReset = () => {
    handleClear();
    setYoutubeUrl('');
  };

  const handleRetry = () => {
    setError(null);
    if (languages.length > 0) {
      handleFetchCaptions();
    } else {
      handleFetchLanguages();
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl text-foreground mb-1 flex items-center gap-2">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Captions className="w-6 h-6 text-purple-500" />
            </div>
            Generate Youtube Caption
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground">
            Extract captions with timestamps from YouTube videos
          </p>
        </div>
      </div>

      <Card className="premium-card">
        <div className="p-5 sm:p-6 border-b border-border bg-gradient-to-r from-purple-500/5 to-transparent">
          <h2 className="text-lg text-foreground flex items-center gap-2">
            <Link2 className="w-5 h-5 text-purple-500" />
            YouTube URL
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Supports all URL formats: regular, shorts, live, and youtu.be links
          </p>
        </div>

        <div className="p-5 sm:p-6 space-y-6">
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              YouTube Video URL <span className="text-red-500">*</span>
            </Label>
            <div className="flex gap-3">
              <Input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
                disabled={isFetchingLanguages || isFetchingCaptions}
                className="bg-background border-input flex-1"
              />
              <Button
                onClick={handleFetchLanguages}
                disabled={isFetchingLanguages || isFetchingCaptions || !youtubeUrl.trim()}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {isFetchingLanguages ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Fetching...
                  </>
                ) : (
                  <>
                    <Globe className="w-4 h-4 mr-2" />
                    Get Languages
                  </>
                )}
              </Button>
            </div>
            {videoId && (
              <p className="text-xs text-muted-foreground">
                Video ID: {videoId}
              </p>
            )}
          </div>

          {languages.length > 0 && (
            <div className="space-y-4 pt-4 border-t border-border">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Globe className="w-4 h-4 text-muted-foreground" />
                    Select Language
                  </Label>
                  <Select value={selectedLanguage} onValueChange={setSelectedLanguage} disabled={isFetchingCaptions}>
                    <SelectTrigger className="bg-background border-input">
                      <SelectValue placeholder="Select language" />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((lang) => (
                        <SelectItem key={lang.code} value={lang.code}>
                          {lang.name} ({lang.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                onClick={handleFetchCaptions}
                disabled={isFetchingCaptions || !selectedLanguage}
                className="gradient-primary"
              >
                {isFetchingCaptions ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Fetching Captions...
                  </>
                ) : (
                  <>
                    <Captions className="w-4 h-4 mr-2" />
                    Fetch Captions
                  </>
                )}
              </Button>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <div className="flex-1">
                <p className="text-sm text-red-400">{error}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRetry}
                className="border-red-500/50 text-red-500 hover:bg-red-500 hover:text-white"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try Again
              </Button>
            </div>
          )}

          <div className="flex gap-3 pt-4 border-t border-border">
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={isFetchingLanguages || isFetchingCaptions}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Reset
            </Button>
          </div>
        </div>
      </Card>

      {captionData && (
        <Card className="premium-card">
          <div className="p-5 sm:p-6 border-b border-border bg-gradient-to-r from-green-500/5 to-transparent">
            <div className="flex items-center justify-between">
              <h2 className="text-lg text-foreground flex items-center gap-2">
                <Captions className="w-5 h-5 text-green-500" />
                Captions ({captionData.captions.length} segments)
              </h2>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground px-2 py-1 bg-accent rounded">
                  Language: {captionData.language}
                </span>
                <Button
                  size="sm"
                  onClick={handleDownload}
                  disabled={isDownloading}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Download .txt
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleClear}
                  className="border-red-500/50 text-red-500 hover:bg-red-500 hover:text-white"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear
                </Button>
              </div>
            </div>
          </div>

          <div className="p-5 sm:p-6">
            <div className="max-h-[500px] overflow-y-auto rounded-lg border border-border bg-slate-900/50">
              <div className="p-4 space-y-3">
                {captionData.captions.map((caption, index) => (
                  <div key={index} className="flex gap-3 group hover:bg-accent/30 p-2 rounded transition-colors">
                    <div className="shrink-0 flex items-center gap-1 text-xs font-mono text-purple-400 bg-purple-500/10 px-2 py-1 rounded">
                      <Clock className="w-3 h-3" />
                      {caption.timestamp}
                    </div>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      {caption.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      <Card className="premium-card">
        <div className="p-5 sm:p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-3">How It Works</h3>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <div className="w-2 h-2 bg-purple-500 rounded-full" />
              Paste any YouTube URL (regular, shorts, live)
            </li>
            <li className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full" />
              Select from available caption languages
            </li>
            <li className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              View captions with timestamps on screen
            </li>
            <li className="flex items-center gap-2">
              <div className="w-2 h-2 bg-orange-500 rounded-full" />
              Download as formatted .txt file
            </li>
          </ul>
          <p className="text-xs text-muted-foreground mt-4 pt-4 border-t border-border">
            Note: Caption files are automatically deleted from the server after download or within 24 hours. Uses RapidAPI with yt-dlp fallback.
          </p>
        </div>
      </Card>
    </div>
  );
}
