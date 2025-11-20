/**
 * Canvas utilities for mask drawing
 */

export const drawOnCanvas = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  brushSize: number,
  isErasing: boolean
) => {
  ctx.globalCompositeOperation = isErasing ? 'destination-out' : 'source-over';
  ctx.fillStyle = isErasing ? 'rgba(0,0,0,1)' : 'rgba(255,255,255,0.7)';
  ctx.beginPath();
  ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2);
  ctx.fill();
};

export const canvasToBlob = (canvas: HTMLCanvasElement): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error('Failed to create blob from canvas'));
      }
    }, 'image/png');
  });
};

export const clearCanvas = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
  ctx.clearRect(0, 0, width, height);
};
