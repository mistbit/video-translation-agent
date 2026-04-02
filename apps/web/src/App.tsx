import React, { useState } from 'react';
import { Upload, Settings, Play, CheckCircle2, FileVideo, ChevronRight, Globe, Volume2, Mic2 } from 'lucide-react';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <div className="min-h-screen bg-white text-[#171717] selection:bg-gray-100">
      {/* Header */}
      <header className="border-b border-gray-100 py-5 px-8 flex items-center justify-between sticky top-0 bg-white/80 backdrop-blur-md z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
            <Play className="w-4 h-4 text-white ml-0.5" />
          </div>
          <span className="font-semibold text-lg tracking-tight">VTL Agent</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium text-gray-500">
          <a href="#" className="text-black transition-colors">Workspace</a>
          <a href="#" className="hover:text-black transition-colors">History</a>
          <a href="#" className="hover:text-black transition-colors">Settings</a>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-semibold tracking-tight mb-3 text-balance">
            Translate & Dub Videos
          </h1>
          <p className="text-gray-500 text-lg">
            Local-first video localization pipeline with high precision.
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="grid md:grid-cols-[1fr_320px] divide-y md:divide-y-0 md:divide-x divide-gray-100">
            
            {/* Left Column: Upload */}
            <div className="p-8 md:p-10 flex flex-col">
              <h2 className="text-lg font-medium mb-6 flex items-center gap-2">
                <FileVideo className="w-5 h-5 text-gray-400" />
                Source Media
              </h2>
              
              <div 
                className={`flex-1 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-8 transition-colors ${
                  isDragging ? 'border-black bg-gray-50' : 'border-gray-200 hover:border-gray-300 bg-gray-50/50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                {file ? (
                  <div className="text-center">
                    <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm border border-gray-100 mx-auto mb-4">
                      <CheckCircle2 className="w-6 h-6 text-black" />
                    </div>
                    <p className="font-medium text-gray-900 truncate max-w-[200px]">{file.name}</p>
                    <p className="text-sm text-gray-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                    <button 
                      onClick={() => setFile(null)}
                      className="text-xs font-medium text-gray-400 hover:text-black mt-4 transition-colors"
                    >
                      Remove file
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm border border-gray-100 mb-4">
                      <Upload className="w-5 h-5 text-gray-600" />
                    </div>
                    <p className="font-medium text-gray-900 mb-1">Upload a video</p>
                    <p className="text-sm text-gray-500 text-center mb-6">
                      Drag and drop your file here, or click to browse
                    </p>
                    <label className="bg-black text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors cursor-pointer shadow-sm">
                      Select File
                      <input type="file" className="hidden" accept="video/*" onChange={handleFileChange} />
                    </label>
                  </>
                )}
              </div>
            </div>

            {/* Right Column: Settings */}
            <div className="p-8 md:p-10 bg-gray-50/30">
              <h2 className="text-lg font-medium mb-6 flex items-center gap-2">
                <Settings className="w-5 h-5 text-gray-400" />
                Configuration
              </h2>

              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <Globe className="w-4 h-4 text-gray-400" />
                    Target Language
                  </label>
                  <select className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/5 appearance-none">
                    <option value="en">English</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                  </select>
                </div>

                <div className="space-y-3">
                  <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <Mic2 className="w-4 h-4 text-gray-400" />
                    Voice Profile
                  </label>
                  <select className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/5 appearance-none">
                    <option value="en_female_neutral_01">English Female Neutral</option>
                    <option value="en_male_neutral_01">English Male Neutral</option>
                  </select>
                </div>

                <div className="space-y-3">
                  <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-gray-400" />
                    Mix Mode
                  </label>
                  <select className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/5 appearance-none">
                    <option value="duck">Duck (Lower background audio)</option>
                    <option value="replace">Replace (Mute original audio)</option>
                  </select>
                </div>

                <div className="pt-6 mt-6 border-t border-gray-100">
                  <button 
                    disabled={!file}
                    className={`w-full py-3 px-4 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all ${
                      file 
                        ? 'bg-black text-white hover:bg-gray-800 shadow-md shadow-black/5' 
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    Start Processing
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
            
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-8 text-center text-sm text-gray-400">
          Powered by local translation and TTS models. No data leaves your machine.
        </div>
      </main>
    </div>
  );
}

export default App;
