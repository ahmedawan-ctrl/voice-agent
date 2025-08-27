import React from 'react';
import MicButton from './MicButton';
import AnimatedBackground from './AnimatedBackground';
import FloatingCharacters from './FloatingCharacters';
import BrandText from './BrandText';

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-black via-gray-900 to-black">
      <AnimatedBackground />
      <FloatingCharacters />
      
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <BrandText />
        <MicButton />
      </div>
    </div>
  );
}
