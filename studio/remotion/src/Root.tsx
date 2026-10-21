import React from 'react';
import { Composition } from 'remotion';
import { KineticCaptions } from './KineticCaptions';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="KineticCaptions"
        component={KineticCaptions}
        durationInFrames={18 * 24}
        fps={24}
        width={1080}
        height={1920}
        defaultProps={{
          quoteText: "HINOKAMI KAGURA! DANCE OF THE FIRE GOD!",
          characterName: "TANJIRO KAMADO",
          accentColor: "#FF3333"
        }}
      />
    </>
  );
};
