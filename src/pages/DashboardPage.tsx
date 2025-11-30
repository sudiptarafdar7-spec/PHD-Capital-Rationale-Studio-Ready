import { useState, useEffect, useCallback, useRef } from 'react';
import { FileText, CheckCircle2, XCircle, Eye, Download, Plus, Search, Calendar, Video, FileSpreadsheet, PenTool, ExternalLink, Clock, X, ChevronLeft, ChevronRight, PlayCircle, FileSignature, Loader2, Layers } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { Calendar as CalendarComponent } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import type { Job, DashboardStats } from '../types';

interface DashboardPageProps {
  onNavigate: (page: string, jobId?: string) => void;
}

const JOBS_PER_PAGE = 20;

export default function DashboardPage({ onNavigate }: DashboardPageProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [toolFilter, setToolFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined);
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined);
  const [calendarMonth, setCalendarMonth] = useState<Date>(new Date());
  const [jobs, setJobs] = useState<Job[]>([]);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [totalJobs, setTotalJobs] = useState(0);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const [stats, setStats] = useState<DashboardStats>({
    total_jobs: 0,
    completed_jobs: 0,
    failed_jobs: 0,
    total_change: '+ 0% from last month',
    completed_change: '+ 0% from last month',
    failed_change: '+ 0% from last month'
  });

  const hasMore = jobs.length < totalJobs;

  const fetchDashboardData = useCallback(async (loadMore: boolean = false) => {
    try {
      const token = localStorage.getItem('token');
      const currentOffset = loadMore ? offset : 0;
      
      if (loadMore) {
        setIsLoadingMore(true);
      } else {
        setIsInitialLoading(true);
      }
      
      // Build query parameters
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (toolFilter !== 'all') params.append('tool', toolFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (dateFrom) params.append('date_from', dateFrom.toISOString().split('T')[0]);
      if (dateTo) params.append('date_to', dateTo.toISOString().split('T')[0]);
      params.append('limit', JOBS_PER_PAGE.toString());
      params.append('offset', currentOffset.toString());

      const response = await fetch(`/api/v1/dashboard?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        
        if (loadMore) {
          setJobs(prev => [...prev, ...(data.jobs || [])]);
        } else {
          setJobs(data.jobs || []);
        }
        
        setTotalJobs(data.total || 0);
        setStats(data.stats || {
          total_jobs: 0,
          completed_jobs: 0,
          failed_jobs: 0,
          total_change: '+ 0% from last month',
          completed_change: '+ 0% from last month',
          failed_change: '+ 0% from last month'
        });
      } else {
        console.error('Failed to fetch dashboard data');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setIsLoadingMore(false);
      setIsInitialLoading(false);
    }
  }, [searchQuery, toolFilter, statusFilter, dateFrom, dateTo, offset]);

  // Initial load and filter changes
  useEffect(() => {
    setOffset(0);
    fetchDashboardData(false);
  }, [searchQuery, toolFilter, statusFilter, dateFrom, dateTo]);

  // Load more when offset changes (but not on initial load)
  useEffect(() => {
    if (offset > 0) {
      fetchDashboardData(true);
    }
  }, [offset]);

  const handleLoadMore = useCallback(() => {
    if (!isLoadingMore && hasMore) {
      setOffset(prev => prev + JOBS_PER_PAGE);
    }
  }, [isLoadingMore, hasMore]);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore && !isInitialLoading) {
          handleLoadMore();
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, isLoadingMore, isInitialLoading, handleLoadMore]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'signed':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'completed':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'pdf_ready':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'processing':
      case 'running':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'signed':
        return <CheckCircle2 className="w-4 h-4" />;
      case 'completed':
        return <FileText className="w-4 h-4" />;
      case 'pdf_ready':
        return <FileText className="w-4 h-4" />;
      case 'failed':
        return <XCircle className="w-4 h-4" />;
      case 'processing':
      case 'running':
        return <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getToolIcon = (tool: string) => {
    switch (tool) {
      case 'Media Rationale':
        return <Video className="w-4 h-4" />;
      case 'Premium Rationale':
        return <FileSpreadsheet className="w-4 h-4" />;
      case 'Manual Rationale':
        return <PenTool className="w-4 h-4" />;
      case 'Bulk Rationale':
        return <Layers className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getToolColor = (tool: string) => {
    switch (tool) {
      case 'Media Rationale':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'Premium Rationale':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'Manual Rationale':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'Bulk Rationale':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  // Jobs are already filtered by backend API
  const filteredJobs = jobs;

  const handleResetFilters = () => {
    setSearchQuery('');
    setToolFilter('all');
    setStatusFilter('all');
    setDateFrom(undefined);
    setDateTo(undefined);
  };

  const hasActiveFilters = searchQuery || toolFilter !== 'all' || statusFilter !== 'all' || dateFrom || dateTo;

  const handleViewDetails = (jobId: string, toolUsed?: string) => {
    // Normalize tool_used to handle both snake_case and Title Case
    const normalizedTool = toolUsed?.toLowerCase().replace(/\s+/g, '_');
    
    // Navigate to the correct tool page based on tool_used or job ID prefix
    if (normalizedTool === 'premium_rationale' || jobId.startsWith('premium-')) {
      onNavigate('premium-rationale', jobId);
    } else if (normalizedTool === 'manual_rationale' || jobId.startsWith('manual-')) {
      onNavigate('manual-rationale', jobId);
    } else if (normalizedTool === 'bulk_rationale' || jobId.startsWith('bulk-')) {
      onNavigate('bulk-rationale', jobId);
    } else {
      // Default to media-rationale
      onNavigate('media-rationale', jobId);
    }
  };

  const handleDownloadPDF = async (jobId: string, signed: boolean = false) => {
    try {
      setDownloadingId(jobId);
      const token = localStorage.getItem('token');
      
      // Determine API endpoint based on job ID prefix
      const apiEndpoint = jobId.startsWith('premium-') 
        ? `/api/v1/premium-rationale/jobs/${jobId}`
        : `/api/v1/media-rationale/job/${jobId}`;
      
      // Fetch job data to get PDF path from saved_rationale table
      const jobResponse = await fetch(apiEndpoint, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!jobResponse.ok) {
        console.error('Failed to fetch job data');
        return;
      }
      
      const jobData = await jobResponse.json();
      let pdfPath = null;
      
      if (signed) {
        // Try both camelCase and snake_case
        pdfPath = jobData.job?.signedPdfPath || jobData.job?.signed_pdf_path;
      } else {
        // For unsigned, try saved_rationale first, then fallback to Step 14
        pdfPath = jobData.job?.unsignedPdfPath || jobData.job?.unsigned_pdf_path;
        if (!pdfPath) {
          // Fallback to Step 14 output for pdf_ready status
          const step14 = jobData.job?.steps?.find((s: any) => s.step_number === 14);
          const outputFiles = step14?.outputFiles || step14?.output_files || [];
          if (outputFiles.length > 0) {
            pdfPath = outputFiles.find((f: string) => f.endsWith('.pdf'));
          }
        }
      }
      
      if (!pdfPath) {
        console.error('PDF path not found');
        return;
      }
      
      const response = await fetch(`/api/v1/saved-rationale/download/${encodeURIComponent(pdfPath)}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `rationale_${jobId}_${signed ? 'signed' : 'unsigned'}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error('Failed to download PDF');
      }
    } catch (error) {
      console.error('Error downloading PDF:', error);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl text-foreground mb-1">Dashboard</h1>
          <p className="text-sm sm:text-base text-muted-foreground">Overview of your rationale generation jobs</p>
        </div>
        <Button
          onClick={() => onNavigate('media-rationale')}
          className="gradient-primary shadow-lg glow-primary w-full sm:w-auto h-11"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Rationale
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="premium-card group">
          <div className="p-5 sm:p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-muted-foreground text-sm mb-2">Total Jobs</p>
                <p className="text-3xl sm:text-4xl text-foreground mb-1.5">{stats.total_jobs}</p>
                <p className="text-sm text-green-500 flex items-center gap-1">
                  {stats.total_change}
                </p>
              </div>
              <div className="p-3 icon-bg-primary rounded-xl transition-all group-hover:scale-110">
                <FileText className="w-6 h-6 text-blue-500" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="premium-card group">
          <div className="p-5 sm:p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-muted-foreground text-sm mb-2">Completed</p>
                <p className="text-3xl sm:text-4xl text-foreground mb-1.5">{stats.completed_jobs}</p>
                <p className="text-sm text-green-500 flex items-center gap-1">
                  {stats.completed_change}
                </p>
              </div>
              <div className="p-3 icon-bg-success rounded-xl transition-all group-hover:scale-110">
                <CheckCircle2 className="w-6 h-6 text-green-500" />
              </div>
            </div>
          </div>
        </Card>

        <Card className="premium-card group">
          <div className="p-5 sm:p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-muted-foreground text-sm mb-2">Failed</p>
                <p className="text-3xl sm:text-4xl text-foreground mb-1.5">{stats.failed_jobs}</p>
                <p className="text-sm text-red-500 flex items-center gap-1">
                  {stats.failed_change}
                </p>
              </div>
              <div className="p-3 icon-bg-danger rounded-xl transition-all group-hover:scale-110">
                <XCircle className="w-6 h-6 text-red-500" />
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Jobs */}
      <Card className="premium-card overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-border bg-gradient-to-r from-blue-500/5 to-transparent">
          <h2 className="text-xl text-foreground flex items-center gap-2">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <FileText className="w-5 h-5 text-blue-500" />
            </div>
            Recent Jobs
          </h2>
        </div>

        {/* Advanced Filters */}
        <div className="p-4 sm:p-6 border-b border-border space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 sm:gap-4">
            {/* Search */}
            <div className="md:col-span-2 xl:col-span-2 space-y-1.5">
              <Label className="text-xs text-muted-foreground">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search by video title, URL, or Job ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-background border-input text-foreground text-sm"
                />
              </div>
            </div>

            {/* Tool Filter */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Filter by Tool</Label>
              <Select value={toolFilter} onValueChange={setToolFilter}>
                <SelectTrigger className="bg-background border-input text-foreground">
                  <SelectValue placeholder="All Tools" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    All Tools
                  </SelectItem>
                  <SelectItem value="media" className="text-foreground focus:bg-accent focus:text-accent-foreground">
                    <div className="flex items-center gap-2">
                      <Video className="w-4 h-4 text-blue-500" />
                      Media Rationale
                    </div>
                  </SelectItem>
                  <SelectItem value="premium" className="text-foreground focus:bg-accent focus:text-accent-foreground">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4 text-purple-500" />
                      Premium Rationale
                    </div>
                  </SelectItem>
                  <SelectItem value="manual" className="text-foreground focus:bg-accent focus:text-accent-foreground">
                    <div className="flex items-center gap-2">
                      <PenTool className="w-4 h-4 text-green-500" />
                      Manual Rationale
                    </div>
                  </SelectItem>
                  <SelectItem value="bulk" className="text-foreground focus:bg-accent focus:text-accent-foreground">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-orange-500" />
                      Bulk Rationale
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Status Filter */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Filter by Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="bg-background border-input text-foreground">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    All Status
                  </SelectItem>
                  <SelectItem value="running">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-blue-500" />
                      Running
                    </div>
                  </SelectItem>
                  <SelectItem value="pdf_ready">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-green-500" />
                      PDF Ready
                    </div>
                  </SelectItem>
                  <SelectItem value="completed">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-amber-500" />
                      Completed
                    </div>
                  </SelectItem>
                  <SelectItem value="signed">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      Signed
                    </div>
                  </SelectItem>
                  <SelectItem value="failed">
                    <div className="flex items-center gap-2">
                      <XCircle className="w-4 h-4 text-red-500" />
                      Failed
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date Range Filter */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Date Range</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left bg-background border-input text-foreground hover:bg-accent hover:text-accent-foreground"
                  >
                    <Calendar className="mr-2 h-4 w-4 text-muted-foreground" />
                    {dateFrom ? (
                      dateTo ? (
                        <span className="text-foreground">
                          {dateFrom.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - {dateTo.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                      ) : (
                        <span className="text-foreground">{dateFrom.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                      )
                    ) : (
                      <span className="text-muted-foreground">Pick a date</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <div className="p-3">
                    {(dateFrom || dateTo) && (
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setDateFrom(undefined);
                          setDateTo(undefined);
                        }}
                        className="w-full mb-2"
                      >
                        <X className="w-4 h-4 mr-2" />
                        Clear dates
                      </Button>
                    )}

                    {/* Month and Year Navigation */}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const newDate = new Date(calendarMonth);
                          newDate.setMonth(newDate.getMonth() - 1);
                          setCalendarMonth(newDate);
                        }}
                        className="h-8 w-8 p-0"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>

                      <div className="flex gap-2">
                        <Select
                          value={calendarMonth.getMonth().toString()}
                          onValueChange={(value) => {
                            const newDate = new Date(calendarMonth);
                            newDate.setMonth(parseInt(value));
                            setCalendarMonth(newDate);
                          }}
                        >
                          <SelectTrigger className="h-8 w-[110px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[
                              'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December'
                            ].map((month, index) => (
                              <SelectItem 
                                key={index} 
                                value={index.toString()}
                              >
                                {month}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <Select
                          value={calendarMonth.getFullYear().toString()}
                          onValueChange={(value) => {
                            const newDate = new Date(calendarMonth);
                            newDate.setFullYear(parseInt(value));
                            setCalendarMonth(newDate);
                          }}
                        >
                          <SelectTrigger className="h-8 w-[80px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - i).map((year) => (
                              <SelectItem 
                                key={year} 
                                value={year.toString()}
                              >
                                {year}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const newDate = new Date(calendarMonth);
                          newDate.setMonth(newDate.getMonth() + 1);
                          setCalendarMonth(newDate);
                        }}
                        className="h-8 w-8 p-0"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>

                    <CalendarComponent
                      mode="range"
                      selected={{ from: dateFrom, to: dateTo }}
                      onSelect={(range) => {
                        setDateFrom(range?.from);
                        setDateTo(range?.to);
                      }}
                      month={calendarMonth}
                      onMonthChange={setCalendarMonth}
                      numberOfMonths={1}
                      hideNavigation={true}
                      className="rounded-md"
                    />
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>

          {/* Active Filters & Clear Button */}
          {hasActiveFilters && (
            <div className="flex items-center justify-between pt-2 border-t border-border">
              <div className="flex items-center gap-2 text-sm text-muted-foreground flex-wrap">
                <span>Active filters:</span>
                {searchQuery && (
                  <Badge variant="outline">
                    Search: "{searchQuery}"
                  </Badge>
                )}
                {toolFilter !== 'all' && (
                  <Badge variant="outline">
                    Tool: {toolFilter === 'media' ? 'Media Rationale' : toolFilter === 'premium' ? 'Premium Rationale' : 'Manual Rationale'}
                  </Badge>
                )}
                {statusFilter !== 'all' && (
                  <Badge variant="outline">
                    Status: {statusFilter}
                  </Badge>
                )}
                {(dateFrom || dateTo) && (
                  <Badge variant="outline">
                    Date: {dateFrom?.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    {dateTo && ` - ${dateTo.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`}
                  </Badge>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetFilters}
              >
                <X className="w-4 h-4 mr-1" />
                Clear All
              </Button>
            </div>
          )}
        </div>

        {/* Jobs List */}
        <div className="divide-y divide-border">
          {isInitialLoading ? (
            <div className="p-12 text-center text-muted-foreground">
              <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-blue-500" />
              <p>Loading jobs...</p>
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>No jobs found</p>
              <p className="text-sm mt-2">Try adjusting your search or filter criteria</p>
            </div>
          ) : (
            filteredJobs.map((job) => (
              <div key={job.id} className="p-4 sm:p-6 hover:bg-gradient-to-r hover:from-blue-500/5 hover:to-transparent transition-all duration-300 border-l-2 border-transparent hover:border-blue-500">
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                  {/* Left Side: Job Info */}
                  <div className="flex gap-3 sm:gap-4 flex-1 min-w-0">
                    <div className="p-2.5 icon-bg-primary rounded-xl h-fit shrink-0">
                      <FileText className="w-5 h-5 text-blue-500" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-2 sm:space-y-3">
                      {/* Job ID and Status */}
                      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                        <span className="text-muted-foreground text-xs sm:text-sm font-mono">Job ID: {job.id}</span>
                        <Badge className={getStatusColor(job.status)}>
                          <span className="flex items-center gap-1 sm:gap-1.5 text-xs sm:text-sm">
                            {getStatusIcon(job.status)}
                            {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                          </span>
                        </Badge>
                      </div>

                      {/* Video Title with YouTube Link */}
                      <div>
                        <a
                          href={job.youtube_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-foreground hover:text-blue-500 transition-colors inline-flex items-center gap-2 group"
                        >
                          <span>{job.title}</span>
                          <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-blue-500" />
                        </a>
                      </div>

                      {/* Metadata Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                        <div className="flex items-center gap-2">
                          <Badge className={getToolColor(job.tool_used)}>
                            <span className="flex items-center gap-1.5">
                              {getToolIcon(job.tool_used)}
                              {job.tool_used}
                            </span>
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <PlayCircle className="w-3.5 h-3.5" />
                          <span className="text-muted-foreground">Channel:</span>
                          <span className="text-foreground">{job.channel_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Clock className="w-3.5 h-3.5" />
                          <span className="text-muted-foreground">Started:</span>
                          <span className="text-foreground">{formatDateTime(job.created_at)}</span>
                        </div>
                      </div>

                      {/* Progress Bar for Running/Processing Jobs */}
                      {(job.status === 'running' || job.status === 'processing') && (
                        <div>
                          <div className="flex items-center justify-between text-sm mb-1.5">
                            <span className="text-muted-foreground">Progress</span>
                            <span className="text-blue-500">{job.progress}%</span>
                          </div>
                          <div className="w-full bg-muted rounded-full h-2">
                            <div
                              className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${job.progress}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Side: Action Buttons */}
                  <div className="flex flex-row gap-2 w-full lg:w-auto lg:flex-col shrink-0">
                    <Button
                      size="sm"
                      onClick={() => handleViewDetails(job.id, job.tool_used)}
                      className="gradient-primary active:scale-95 transition-all duration-200 hover:shadow-lg flex-1 sm:flex-initial lg:min-w-[140px] h-9"
                    >
                      <Eye className="w-4 h-4 mr-1.5" />
                      <span className="hidden sm:inline">View Details</span>
                      <span className="sm:hidden">View</span>
                    </Button>
                    
                    {/* Signed: Download Signed PDF */}
                    {job.status === 'signed' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownloadPDF(job.id, true)}
                        disabled={downloadingId === job.id}
                        className="border-purple-500/50 text-purple-500 hover:bg-purple-500 hover:text-white hover:border-purple-500 active:scale-95 transition-all duration-200 hover:shadow-lg flex-1 sm:flex-initial lg:min-w-[140px] h-9 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {downloadingId === job.id ? (
                          <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                        ) : (
                          <Download className="w-4 h-4 mr-1.5" />
                        )}
                        <span>Signed</span>
                      </Button>
                    )}
                    
                    {/* Completed: Download Unsigned PDF + Sign Now */}
                    {job.status === 'completed' && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDownloadPDF(job.id, false)}
                          disabled={downloadingId === job.id}
                          className="border-blue-500/50 text-blue-500 hover:bg-blue-500 hover:text-white hover:border-blue-500 active:scale-95 transition-all duration-200 hover:shadow-lg flex-1 sm:flex-initial lg:min-w-[140px] h-9 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {downloadingId === job.id ? (
                            <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                          ) : (
                            <Download className="w-4 h-4 mr-1.5" />
                          )}
                          <span>Unsigned</span>
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleViewDetails(job.id, job.tool_used)}
                          className="border-green-500/50 text-green-500 hover:bg-green-500 hover:text-white hover:border-green-500 active:scale-95 transition-all duration-200 hover:shadow-lg flex-1 sm:flex-initial lg:min-w-[140px] h-9"
                        >
                          <FileSignature className="w-4 h-4 mr-1.5" />
                          <span className="hidden sm:inline">Sign Now</span>
                          <span className="sm:hidden">Sign</span>
                        </Button>
                      </>
                    )}
                    
                    {/* PDF Ready: Download PDF */}
                    {job.status === 'pdf_ready' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownloadPDF(job.id, false)}
                        disabled={downloadingId === job.id}
                        className="border-blue-500/50 text-blue-500 hover:bg-blue-500 hover:text-white hover:border-blue-500 active:scale-95 transition-all duration-200 hover:shadow-lg flex-1 sm:flex-initial lg:min-w-[140px] h-9 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {downloadingId === job.id ? (
                          <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                        ) : (
                          <Download className="w-4 h-4 mr-1.5" />
                        )}
                        <span>Unsigned</span>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          
          {/* Infinite Scroll Trigger & Load More */}
          {!isInitialLoading && filteredJobs.length > 0 && (
            <div ref={loadMoreRef} className="p-6 text-center">
              {isLoadingMore ? (
                <div className="flex items-center justify-center gap-3 text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                  <span>Loading more jobs...</span>
                </div>
              ) : hasMore ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Showing {jobs.length} of {totalJobs} jobs
                  </p>
                  <Button
                    variant="outline"
                    onClick={handleLoadMore}
                    className="border-blue-500/50 text-blue-500 hover:bg-blue-500 hover:text-white"
                  >
                    Load More Jobs
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Showing all {totalJobs} jobs
                </p>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
