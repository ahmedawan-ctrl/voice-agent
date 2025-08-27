import React from 'react';

export default function AnimatedBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Diagonal neon streaks */}
      <div className="absolute inset-0">
        <div className="absolute top-0 left-0 w-full h-full opacity-30">
          <div className="absolute top-1/4 -left-1/4 w-1/2 h-px bg-gradient-to-r from-transparent via-purple-500 to-transparent transform rotate-45 animate-pulse"></div>
          <div className="absolute top-1/2 -right-1/4 w-1/2 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent transform -rotate-45 animate-pulse delay-1000"></div>
          <div className="absolute bottom-1/4 -left-1/4 w-1/2 h-px bg-gradient-to-r from-transparent via-magenta-500 to-transparent transform rotate-45 animate-pulse delay-2000"></div>
        </div>
      </div>

      {/* Floating particles */}
      {Array.from({ length: 20 }).map((_, i) => (
        <div
          key={i}
          className="absolute w-1 h-1 bg-purple-400 rounded-full opacity-0 animate-firefly"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 5}s`,
            animationDuration: `${3 + Math.random() * 4}s`,
          }}
        ></div>
      ))}

      {/* Gradient waves */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-purple-600/20 via-transparent to-cyan-600/20 animate-wave"></div>
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-tl from-magenta-600/20 via-transparent to-purple-600/20 animate-wave-reverse"></div>
      </div>
    </div>
  );
}
