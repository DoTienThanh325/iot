import { useRef, useCallback, useEffect } from 'react';
import useEmergencyStore from '../store/useEmergencyStore';

export const useAudioAlert = () => {
  const isMuted = useEmergencyStore((state) => state.isMuted);
  const audioCtxRef = useRef(null);
  const intervalRef = useRef(null);

  const initAudio = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        audioCtxRef.current = new AudioCtx();
      }
    }
    if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
  }, []);

  const playSingleBeep = useCallback((freq = 880, duration = 0.18, type = 'sawtooth') => {
    if (isMuted) return;
    try {
      initAudio();
      const ctx = audioCtxRef.current;
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);

      // Volume envelope to avoid click noise
      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.warn('Audio alert error:', e);
    }
  }, [initAudio, isMuted]);

  // Âm thanh báo động liên tục cấp cứu (Medical Emergency Siren: High-Low beep)
  const startAlarm = useCallback(() => {
    if (intervalRef.current) return;
    initAudio();

    let toggle = false;
    // Bíp đầu tiên
    playSingleBeep(960, 0.2, 'sawtooth');

    intervalRef.current = setInterval(() => {
      toggle = !toggle;
      const freq = toggle ? 1200 : 800;
      playSingleBeep(freq, 0.18, 'sawtooth');
    }, 350);
  }, [initAudio, playSingleBeep]);

  const stopAlarm = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
      }
    };
  }, []);

  return {
    playSingleBeep,
    startAlarm,
    stopAlarm,
  };
};

export default useAudioAlert;
