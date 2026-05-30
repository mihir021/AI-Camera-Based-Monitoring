import React, { useState, useRef, useEffect } from 'react';
import {
  Upload, Play, AlertCircle,
  Camera, MonitorPlay,
  ScanLine, FileVideo, LayoutDashboard, Settings2
} from 'lucide-react';

interface Analytics {
  person_count: number;
  fps: number;
  confidence_avg: number;
  frame_number: number;
  total_frames: number;
}

function App() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<Analytics>({
    person_count: 0, fps: 0, confidence_avg: 0, frame_number: 0, total_frames: 0,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Poll analytics
  useEffect(() => {
    if (!videoId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/analytics');
        if (res.ok) setAnalytics(await res.json());
      } catch { /* ignore */ }
    }, 500);
    return () => clearInterval(interval);
  }, [videoId]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    setVideoId(null);
    setFileName(file.name);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST', body: formData,
      });
      if (!response.ok) throw new Error(`Upload failed (${response.status})`);
      const data = await response.json();
      setVideoId(data.video_id);
    } catch (err: any) {
      setError(err.message || 'Upload failed. Is the backend running on port 8000?');
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => fileInputRef.current?.click();

  const progress = analytics.total_frames > 0
    ? Math.round((analytics.frame_number / analytics.total_frames) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-black text-white font-['Inter'] selection:bg-blue-500/30">
      
      {/* ───── Navbar ───── */}
      <nav className="sticky top-0 z-50 border-b border-[#262626] bg-black/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-white text-black flex items-center justify-center">
              <Camera className="w-4 h-4" />
            </div>
            <span className="font-semibold text-sm tracking-tight">AI Monitor</span>
            <div className="h-4 w-px bg-[#262626] mx-2" />
            <span className="text-[#a3a3a3] text-sm">Zone A</span>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium text-[#a3a3a3]">
            <div className="flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer">
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </div>
            <div className="flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer">
              <Settings2 className="w-4 h-4" />
              <span>Settings</span>
            </div>
            <div className="h-4 w-px bg-[#262626]" />
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-[#262626] bg-[#0a0a0a]">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>System Active</span>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        
        {/* Header Title */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight mb-1">Classroom Overview</h1>
          <p className="text-[#a3a3a3] text-sm">Real-time object detection and density analytics.</p>
        </div>

        {/* ───── Top Stats Row ───── */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Students Detected"
            value={videoId ? analytics.person_count.toString() : '—'}
            trend={videoId ? "Live" : "Waiting"}
            trendColor={videoId ? "text-emerald-500" : "text-[#a3a3a3]"}
          />
          <StatCard
            title="Processing Speed"
            value={videoId ? `${analytics.fps} fps` : '—'}
            trend={videoId ? "Stable" : "Waiting"}
            trendColor="text-[#a3a3a3]"
          />
          <StatCard
            title="Avg Confidence"
            value={videoId ? `${(analytics.confidence_avg * 100).toFixed(1)}%` : '—'}
            trend={videoId ? "High Accuracy" : "Waiting"}
            trendColor={videoId ? "text-blue-500" : "text-[#a3a3a3]"}
          />
          <StatCard
            title="Analysis Progress"
            value={videoId ? `${progress}%` : '—'}
            trend={videoId ? `${analytics.frame_number} / ${analytics.total_frames}` : "Waiting"}
            trendColor="text-[#a3a3a3]"
          />
        </div>

        {/* ───── Main Content Grid ───── */}
        <div className="grid grid-cols-3 gap-6">
          
          {/* Main Video Area */}
          <div className="col-span-2 space-y-6">
            
            <div className="glass-panel overflow-hidden flex flex-col group relative">
              <div className="px-4 py-3 border-b border-[#262626] bg-[#0a0a0a] flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <MonitorPlay className="w-4 h-4 text-[#a3a3a3]" />
                  <span>Camera Feed</span>
                </div>
                {videoId && (
                  <div className="flex items-center gap-2">
                    <span className="relative flex w-2 h-2">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75 animate-ping" />
                      <span className="relative inline-flex rounded-full w-2 h-2 bg-red-500" />
                    </span>
                    <span className="text-[10px] font-bold text-red-500 uppercase tracking-widest">Live</span>
                  </div>
                )}
              </div>

              <div className="aspect-[16/9] bg-[#050505] flex items-center justify-center relative">
                {!videoId && !isUploading ? (
                  <div className="text-center">
                    <div className="w-12 h-12 rounded-full border border-[#262626] bg-[#0a0a0a] flex items-center justify-center mx-auto mb-3">
                      <Play className="w-5 h-5 text-[#a3a3a3] ml-1" />
                    </div>
                    <p className="text-sm font-medium">No Feed Available</p>
                    <p className="text-xs text-[#a3a3a3] mt-1">Upload a source to begin processing.</p>
                  </div>
                ) : isUploading ? (
                  <div className="text-center">
                    <ScanLine className="w-8 h-8 text-[#a3a3a3] mx-auto mb-3 animate-pulse-slow" />
                    <p className="text-sm font-medium">Initializing Engine...</p>
                  </div>
                ) : (
                  <img
                    src={`http://localhost:8000/stream/${videoId}`}
                    alt="AI Processed Stream"
                    className="w-full h-full object-contain"
                  />
                )}
              </div>

              {/* Minimal Progress Bar */}
              {videoId && (
                <div className="h-0.5 bg-[#262626] w-full absolute bottom-0 left-0">
                  <div 
                    className="h-full bg-blue-500 transition-all duration-300" 
                    style={{ width: `${progress}%` }} 
                  />
                </div>
              )}
            </div>

          </div>

          {/* Sidebar */}
          <div className="col-span-1 space-y-4">
            
            <div className="glass-panel p-4">
              <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
                <Upload className="w-4 h-4 text-[#a3a3a3]" />
                Video Source
              </h3>
              
              <input
                type="file" accept="video/*" className="hidden" ref={fileInputRef}
                onChange={handleFileUpload}
                onClick={(e) => { (e.target as HTMLInputElement).value = ''; }}
                disabled={isUploading}
              />
              
              <button
                onClick={triggerFileInput}
                disabled={isUploading}
                className="w-full py-8 border border-dashed border-[#262626] rounded-lg hover:border-[#404040] hover:bg-[#0a0a0a] transition-all disabled:opacity-50 flex flex-col items-center justify-center gap-2"
              >
                <Upload className="w-5 h-5 text-[#a3a3a3]" />
                <span className="text-sm font-medium">
                  {isUploading ? 'Uploading...' : 'Select File'}
                </span>
                <span className="text-xs text-[#a3a3a3]">MP4, AVI, MOV</span>
              </button>

              {fileName && !error && (
                <div className="mt-3 px-3 py-2 bg-[#0a0a0a] border border-[#262626] rounded-md flex items-center gap-2">
                  <FileVideo className="w-3.5 h-3.5 text-[#a3a3a3] shrink-0" />
                  <span className="text-xs text-[#a3a3a3] truncate">{fileName}</span>
                </div>
              )}

              {error && (
                <div className="mt-3 p-3 bg-red-950/30 border border-red-900/50 rounded-md flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
                  <span className="text-xs text-red-200">{error}</span>
                </div>
              )}
            </div>

            <div className="glass-panel p-4">
               <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-[#a3a3a3]" />
                Configuration
              </h3>
              
              <div className="space-y-3">
                <ConfigRow label="Model" value="YOLOv8 Nano" />
                <ConfigRow label="Confidence" value="≥ 55%" />
                <ConfigRow label="Target" value="Person" />
                <ConfigRow label="Backend" value="FastAPI" />
                <ConfigRow 
                  label="Status" 
                  value={videoId ? 'Active' : 'Idle'} 
                  valueColor={videoId ? 'text-emerald-500' : 'text-[#a3a3a3]'} 
                />
              </div>
            </div>

          </div>
        </div>

      </main>
    </div>
  );
}

function StatCard({ title, value, trend, trendColor }: { title: string, value: string, trend: string, trendColor: string }) {
  return (
    <div className="glass-panel p-5 flex flex-col gap-1">
      <span className="text-xs font-medium text-[#a3a3a3]">{title}</span>
      <span className="text-2xl font-semibold stat-value">{value}</span>
      <span className={`text-xs mt-2 ${trendColor}`}>{trend}</span>
    </div>
  );
}

function ConfigRow({ label, value, valueColor = 'text-white' }: { label: string, value: string, valueColor?: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[#a3a3a3]">{label}</span>
      <span className={`font-medium ${valueColor}`}>{value}</span>
    </div>
  );
}

export default App;
