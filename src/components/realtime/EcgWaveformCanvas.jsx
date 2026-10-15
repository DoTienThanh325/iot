import React, { useRef, useEffect, useState } from 'react';
import { Box, Paper, Typography, Chip, Tooltip, IconButton } from '@mui/material';
import { Refresh as RefreshIcon, ZoomIn as ZoomInIcon, ZoomOut as ZoomOutIcon } from '@mui/icons-material';

export const EcgWaveformCanvas = ({ ecgBufferRef }) => {
  const canvasRef = useRef(null);
  const animFrameIdRef = useRef(null);

  // Buffer hiển thị trên màn hình: 625 mẫu = 5 giây sóng ở 125Hz
  const BUFFER_SIZE = 625;
  const displayBufferRef = useRef(new Array(BUFFER_SIZE).fill(512));
  const writeIndexRef = useRef(0);

  // Scale gain
  const [gain, setGain] = useState(1.0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Tự động điều chỉnh kích thước Canvas theo pixel density (Retina display)
    const updateCanvasSize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);

    // Vẽ lưới điện tâm đồ chuẩn y tế (Medical ECG Paper Grid)
    const drawGrid = (width, height) => {
      ctx.fillStyle = '#051314'; // Dark teal medical oscilloscope background
      ctx.fillRect(0, 0, width, height);

      // Ô nhỏ (1mm equivalent ~ 5px)
      ctx.lineWidth = 0.5;
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.08)';
      ctx.beginPath();
      for (let x = 0; x < width; x += 10) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let y = 0; y < height; y += 10) {
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();

      // Ô lớn (5mm equivalent ~ 25px hoặc 50px)
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.2)';
      ctx.beginPath();
      for (let x = 0; x < width; x += 50) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let y = 0; y < height; y += 50) {
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();
    };

    // Hàm vòng lặp render ở 60 FPS
    const render = () => {
      // 1. Lấy mẫu từ ecgBufferRef và đẩy vào displayBufferRef
      if (ecgBufferRef && ecgBufferRef.current && ecgBufferRef.current.length > 0) {
        // Lấy ra một lượng mẫu tương ứng với tốc độ quét
        const samplesToConsume = Math.min(ecgBufferRef.current.length, 10);
        for (let i = 0; i < samplesToConsume; i++) {
          const sample = ecgBufferRef.current.shift();
          displayBufferRef.current[writeIndexRef.current] = sample;
          writeIndexRef.current = (writeIndexRef.current + 1) % BUFFER_SIZE;
        }
      }

      const rect = canvas.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;

      // Xoá và vẽ lại lưới
      drawGrid(width, height);

      // 2. Vẽ đường sóng ECG
      ctx.save();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#00ff88'; // Fluorescent ECG Green
      ctx.shadowColor = '#00ff88';
      ctx.shadowBlur = 4;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      const baseline = height / 2;
      const stepX = width / BUFFER_SIZE;

      ctx.beginPath();
      for (let i = 0; i < BUFFER_SIZE; i++) {
        // Tín hiệu ADC 10-bit nằm khoảng 0 - 1023, trung tâm là 512
        const raw = displayBufferRef.current[i] ?? 512;
        // Chuẩn hóa [-1, 1] rồi scale theo chiều cao canvas
        const normalized = ((raw - 512) / 300) * gain;
        const y = baseline - normalized * (height * 0.35);
        const x = i * stepX;

        // Bỏ qua một đoạn ngắn ngay trước con trỏ quét (Sweep gap)
        const sweepGap = 15;
        const currentIndex = writeIndexRef.current;
        const isNearCursor = (i >= currentIndex && i < currentIndex + sweepGap) ||
                             (currentIndex + sweepGap >= BUFFER_SIZE && i < (currentIndex + sweepGap) % BUFFER_SIZE);

        if (isNearCursor) {
          ctx.stroke();
          ctx.beginPath();
          continue;
        }

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
      ctx.restore();

      // 3. Vẽ con trỏ quét (Sweep Head Cursor)
      const cursorX = writeIndexRef.current * stepX;
      ctx.save();
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cursorX, 0);
      ctx.lineTo(cursorX, height);
      ctx.stroke();
      ctx.restore();

      animFrameIdRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
      window.removeEventListener('resize', updateCanvasSize);
    };
  }, [ecgBufferRef, gain]);

  return (
    <Paper
      elevation={0}
      sx={{
        backgroundColor: '#1e293b',
        borderRadius: '12px',
        border: '1px solid #334155',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Waveform Header Bar */}
      <Box
        sx={{
          px: 2,
          py: 1,
          backgroundColor: '#0f172a',
          borderBottom: '1px solid #334155',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#10b981', letterSpacing: '0.5px' }}>
            ĐIỆN TÂM ĐỒ THỜI GIAN THỰC (AD8232 — CHUYỂN ĐẠO II)
          </Typography>
          <Chip label="125 Hz / 60 FPS" size="small" sx={{ backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981', height: 20, fontSize: '0.7rem' }} />
          <Chip label="25 mm/s - 10 mm/mV" size="small" sx={{ backgroundColor: '#1e293b', color: '#94a3b8', height: 20, fontSize: '0.7rem' }} />
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title="Thu nhỏ biên độ">
            <IconButton size="small" onClick={() => setGain((g) => Math.max(0.5, g - 0.25))} sx={{ color: '#94a3b8' }}>
              <ZoomOutIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Typography variant="caption" sx={{ color: '#e2e8f0', minWidth: 40, textAlign: 'center' }}>
            {gain.toFixed(1)}x
          </Typography>
          <Tooltip title="Phóng to biên độ">
            <IconButton size="small" onClick={() => setGain((g) => Math.min(3.0, g + 0.25))} sx={{ color: '#94a3b8' }}>
              <ZoomInIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Làm mới đường sóng">
            <IconButton
              size="small"
              onClick={() => {
                displayBufferRef.current.fill(512);
                if (ecgBufferRef?.current) ecgBufferRef.current = [];
              }}
              sx={{ color: '#94a3b8' }}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Canvas Element */}
      <Box sx={{ position: 'relative', width: '100%', height: 240 }}>
        <canvas
          ref={canvasRef}
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
          }}
        />
        {/* Subtle watermark / telemetry stamp */}
        <Typography
          variant="caption"
          sx={{
            position: 'absolute',
            bottom: 8,
            right: 12,
            color: 'rgba(16, 185, 129, 0.4)',
            fontFamily: 'Roboto Mono, monospace',
            fontSize: '0.68rem',
            userSelect: 'none',
          }}
        >
          LIVE AD8232 TELEMETRY • HIGH-SPEED CANVAS ENGINE
        </Typography>
      </Box>
    </Paper>
  );
};

export default EcgWaveformCanvas;
