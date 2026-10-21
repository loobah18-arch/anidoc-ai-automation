import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export interface CaptionProps {
  quoteText?: string;
  characterName?: string;
  accentColor?: string;
}

export const KineticCaptions: React.FC<CaptionProps> = ({
  quoteText = "HINOKAMI KAGURA! DANCE OF THE FIRE GOD!",
  characterName = "TANJIRO KAMADO",
  accentColor = "#FF3333"
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const words = quoteText.toUpperCase().split(" ");
  const currentWordIndex = Math.min(
    words.length - 1,
    Math.floor(frame / (fps * 0.45))
  );

  const scaleSpring = spring({
    frame: frame % Math.floor(fps * 0.45),
    fps,
    config: {
      damping: 12,
      mass: 0.5,
      stiffness: 200
    }
  });

  return (
    <div
      style={{
        width: 1080,
        height: 1920,
        backgroundColor: 'transparent',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'Impact, sans-serif',
        textAlign: 'center',
        padding: '0 60px',
        boxSizing: 'border-box'
      }}
    >
      <div
        style={{
          fontSize: 84,
          color: '#FFFFFF',
          textShadow: `0 0 20px ${accentColor}, 0 0 40px #000000, 4px 4px 0 #000000`,
          transform: `scale(${1 + scaleSpring * 0.15})`,
          lineHeight: 1.2,
          letterSpacing: 2
        }}
      >
        {words[currentWordIndex]}
      </div>
      <div
        style={{
          marginTop: 30,
          fontSize: 32,
          color: accentColor,
          letterSpacing: 6,
          fontWeight: 'bold',
          textShadow: '2px 2px 0 #000000'
        }}
      >
        — {characterName} —
      </div>
    </div>
  );
};
