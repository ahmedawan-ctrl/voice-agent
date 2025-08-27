import React from 'react';

export default function FloatingCharacters() {
  const characters = [
    { emoji: '✨', size: 'text-2xl', delay: 0 },
    { emoji: '🌟', size: 'text-xl', delay: 1 },
    { emoji: '💫', size: 'text-lg', delay: 2 },
    { emoji: '⭐', size: 'text-xl', delay: 3 },
    { emoji: '🔮', size: 'text-lg', delay: 4 },
    { emoji: '💎', size: 'text-xl', delay: 5 },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none">
      {characters.map((char, index) => (
        <div
          key={index}
          className={`absolute ${char.size} animate-orbit opacity-60 hover:opacity-100 transition-opacity duration-300`}
          style={{
            left: `${20 + (index * 15)}%`,
            top: `${30 + (index * 10)}%`,
            animationDelay: `${char.delay}s`,
            animationDuration: `${8 + Math.random() * 4}s`,
          }}
        >
          <span className="drop-shadow-lg filter">{char.emoji}</span>
        </div>
      ))}

      {/* Abstract neon blobs */}
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={`blob-${i}`}
          className="absolute w-3 h-3 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 opacity-40 animate-drift"
          style={{
            left: `${Math.random() * 80 + 10}%`,
            top: `${Math.random() * 80 + 10}%`,
            animationDelay: `${Math.random() * 6}s`,
            animationDuration: `${6 + Math.random() * 6}s`,
          }}
        ></div>
      ))}

      {/* Kawaii-style elements */}
      <div className="absolute top-1/4 left-1/4 w-4 h-4 bg-pink-400 rounded-full opacity-50 animate-bounce-slow" style={{ animationDelay: '1s' }}>
        <div className="absolute top-1 left-1 w-1 h-1 bg-white rounded-full"></div>
        <div className="absolute top-1 right-1 w-1 h-1 bg-white rounded-full"></div>
      </div>

      <div className="absolute top-3/4 right-1/4 w-6 h-6 bg-cyan-400 rounded-full opacity-50 animate-bounce-slow" style={{ animationDelay: '3s' }}>
        <div className="absolute top-2 left-1.5 w-1 h-1 bg-white rounded-full"></div>
        <div className="absolute top-2 right-1.5 w-1 h-1 bg-white rounded-full"></div>
        <div className="absolute bottom-1.5 left-1/2 transform -translate-x-1/2 w-2 h-0.5 bg-white rounded-full"></div>
      </div>
    </div>
  );
}
