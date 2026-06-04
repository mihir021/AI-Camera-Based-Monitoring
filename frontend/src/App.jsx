import React, { useState, useRef, useEffect } from 'react';
import {
  Upload, Play, AlertCircle,
  Camera, MonitorPlay,
  ScanLine, FileVideo, LayoutDashboard, Settings2
} from 'lucide-react';



function App() {
  const [videoId, setVideoId] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [liveUrl, setLiveUrl] = useState('');
  const [isLiveUrlActive, setIsLiveUrlActive] = useState(false);
  const [analytics, setAnalytics] = useState({
    person_count: 0, fps: 0, confidence_avg: 0, frame_number: 0, total_frames: 0,
  });
  const fileInputRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Poll analytics
  useEffect(() => {
    if (!videoId && !isLiveUrlActive) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/analytics`);
        if (res.ok) setAnalytics(await res.json());
      } catch { /* ignore */ }
    }, 500);
    return () => clearInterval(interval);
  }, [videoId, isLiveUrlActive]);

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    setVideoId(null);
    setIsLiveUrlActive(false);
    setFileName(file.name);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST', body: formData,
      });
      if (!response.ok) throw new Error(`Upload failed (${response.status})`);
      const data = await response.json();
      setVideoId(data.video_id);
    } catch (err) {
      setError(err.message || 'Upload failed. Is the backend running on port 8000?');
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => fileInputRef.current?.click();

  const handleConnectLiveUrl = () => {
    if (!liveUrl.trim()) return;
    
    let processedUrl = liveUrl.trim();
    if (processedUrl.startsWith('http') && !processedUrl.endsWith('/video') && !processedUrl.endsWith('.m3u8')) {
       processedUrl += '/video';
       setLiveUrl(processedUrl);
    }

    setVideoId(null);
    setFileName('Live Camera Feed');
    setIsLiveUrlActive(true);
  };

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
            value={(videoId || isLiveUrlActive) ? analytics.person_count.toString() : '—'}
            trend={(videoId || isLiveUrlActive) ? "Live" : "Waiting"}
            trendColor={(videoId || isLiveUrlActive) ? "text-emerald-500" : "text-[#a3a3a3]"}
          />
          <StatCard
            title="Processing Speed"
            value={(videoId || isLiveUrlActive) ? `${analytics.fps} fps` : '—'}
            trend={(videoId || isLiveUrlActive) ? "Stable" : "Waiting"}
            trendColor="text-[#a3a3a3]"
          />
          <StatCard
            title="Avg Confidence"
            value={(videoId || isLiveUrlActive) ? `${(analytics.confidence_avg * 100).toFixed(1)}%` : '—'}
            trend={(videoId || isLiveUrlActive) ? "High Accuracy" : "Waiting"}
            trendColor={(videoId || isLiveUrlActive) ? "text-blue-500" : "text-[#a3a3a3]"}
          />
          <StatCard
            title="Analysis Progress"
            value={(videoId || isLiveUrlActive) ? (isLiveUrlActive ? 'LIVE' : `${progress}%`) : '—'}
            trend={(videoId || isLiveUrlActive) ? (isLiveUrlActive ? 'Streaming' : `${analytics.frame_number} / ${analytics.total_frames}`) : "Waiting"}
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
                {(videoId || isLiveUrlActive) && (
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
                {!videoId && !isLiveUrlActive && !isUploading ? (
                  <div className="text-center">
                    <div className="w-12 h-12 rounded-full border border-[#262626] bg-[#0a0a0a] flex items-center justify-center mx-auto mb-3">
                      <Play className="w-5 h-5 text-[#a3a3a3] ml-1" />
                    </div>
                    <p className="text-sm font-medium">No Feed Available</p>
                    <p className="text-xs text-[#a3a3a3] mt-1">Upload a source or connect a camera to begin.</p>
                  </div>
                ) : isUploading ? (
                  <div className="text-center">
                    <ScanLine className="w-8 h-8 text-[#a3a3a3] mx-auto mb-3 animate-pulse-slow" />
                    <p className="text-sm font-medium">Initializing Engine...</p>
                  </div>
                ) : (
                  <img
                    src={isLiveUrlActive ? `${API_URL}/stream-url?url=${encodeURIComponent(liveUrl)}` : `${API_URL}/stream/${videoId}`}
                    alt="AI Processed Stream"
                    className="w-full h-full object-contain"
                  />
                )}
              </div>

              {/* Minimal Progress Bar */}
              {videoId && !isLiveUrlActive && (
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
                onClick={(e) => { e.target.value = ''; }}
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

              <div className="my-4 flex items-center gap-2 text-[#a3a3a3]">
                <div className="h-px bg-[#262626] flex-1"></div>
                <span className="text-xs uppercase tracking-widest font-bold">OR</span>
                <div className="h-px bg-[#262626] flex-1"></div>
              </div>

              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder="http://192.168.x.x:8080/video" 
                  value={liveUrl}
                  onChange={(e) => setLiveUrl(e.target.value)}
                  className="flex-1 bg-[#0a0a0a] border border-[#262626] rounded-md px-3 py-2 text-sm text-white placeholder-[#525252] focus:outline-none focus:border-[#404040]"
                />
                <button 
                  onClick={handleConnectLiveUrl}
                  className="px-4 bg-[#262626] hover:bg-[#404040] rounded-md text-sm font-medium transition-colors"
                >
                  Connect
                </button>
              </div>


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
                <ConfigRow label="Model" value="YOLOv8 Small" />
                <ConfigRow label="Confidence" value="≥ 45%" />
                <ConfigRow label="Target" value="Person" />
                <ConfigRow label="Backend" value="FastAPI (GPU)" />
                <ConfigRow 
                  label="Status" 
                  value={(videoId || isLiveUrlActive) ? 'Active' : 'Idle'} 
                  valueColor={(videoId || isLiveUrlActive) ? 'text-emerald-500' : 'text-[#a3a3a3]'} 
                />
              </div>
            </div>

          </div>
        </div>

      </main>
    </div>
  );
}

function StatCard({ title, value, trend, trendColor }) {
  return (
    <div className="glass-panel p-5 flex flex-col gap-1">
      <span className="text-xs font-medium text-[#a3a3a3]">{title}</span>
      <span className="text-2xl font-semibold stat-value">{value}</span>
      <span className={`text-xs mt-2 ${trendColor}`}>{trend}</span>
    </div>
  );
}

function ConfigRow({ label, value, valueColor = 'text-white' }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[#a3a3a3]">{label}</span>
      <span className={`font-medium ${valueColor}`}>{value}</span>
    </div>
  );
}

export default App;
